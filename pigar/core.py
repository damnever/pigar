from .dist import DEFAULT_PYPI_INDEX_URL

import os
import io
import os.path
import sys
import collections
import contextlib
import functools
import importlib
import importlib.util
import importlib.machinery
from typing import NamedTuple, List, Dict, Any, Optional, Tuple
import asyncio

from .db import database
from .log import logger
from .helpers import (
    Color, parse_requirements, PraseRequirementError, trim_prefix, trim_suffix,
    is_commonpath, determine_python_sys_lib_paths, is_site_packages_path
)
from .parser import parse_imports, Module
from .dist import (
    installed_distributions_by_top_level_import_names, installed_distributions,
    FrozenRequirement, _all_hardcode_import_names, DEFAULT_PYPI_INDEX_URL,
    PyPIDistributions, PyPIDistributionsIndexSynchronizer, canonicalize_name
)

_special_import_names = _all_hardcode_import_names()


class _Locations(dict):
    """_Locations store code locations(file, linenos)."""

    def __init__(self):
        super(_Locations, self).__init__()
        self._sorted = None

    @classmethod
    def build_from(cls, file, lineno):
        self = cls()
        self.add(file, lineno)
        return self

    def add(self, file, lineno):
        if file in self and lineno not in self[file]:
            self[file].append(lineno)
        else:
            self[file] = [lineno]

    def extend(self, obj):
        for file, linenos in obj.items():
            for lineno in linenos:
                self.add(file, lineno)

    def sorted_items(self):
        if self._sorted is None:
            self._sorted = [
                '{0}: {1}'.format(f, ','.join([str(n) for n in sorted(ls)]))
                for f, ls in sorted(self.items())
            ]
        return self._sorted


class _LocatableRequirements(dict):

    class _Requirement(NamedTuple):
        req: FrozenRequirement
        locations: _Locations
        from_annotation: bool

        def format_as_text(
            self,
            package_root_parent: str,
            with_locations: bool = False,
            operator: str = '=='
        ):
            comments = ''
            if with_locations and len(self.locations) > 0:
                if self.from_annotation:
                    comments += '# FROM `requirement-annotations`\n'
                comments += '\n'.join(
                    '# {0}'.format(trim_prefix(c, package_root_parent))
                    for c in self.locations.sorted_items()
                )
                comments += '\n'

            return comments + self.req.as_requirement(operator=operator) + '\n'

    def __init__(self):
        super(_LocatableRequirements, self).__init__()
        self._sorted = None

    def add_locs(
        self,
        req: FrozenRequirement,
        locs: _Locations,
        from_annotation: bool = False,
    ):
        if req.name in self:
            self[req.name].locations.extend(locs)
        else:
            self[req.name] = self._Requirement(req, locs, from_annotation)

    def add(
        self,
        req: FrozenRequirement,
        file: str,
        lineno: int,
        from_annotation: bool = False,
    ):
        if req.name in self:
            self[req.name].locations.add(file, lineno)
        else:
            loc = _Locations()
            loc.add(file, lineno)
            self[req.name] = self._Requirement(req, loc, from_annotation)

    def sorted_items(self):
        if self._sorted is None:
            self._sorted = sorted(
                self.items(), key=lambda item: item[0].lower()
            )
        return self._sorted

    def remove(self, *names):
        for name in names:
            if name in self:
                self.pop(name)
        self._sorted = None


class RequirementsAnalyzer(object):

    def __init__(self, project_root):
        self._project_root = project_root

        self._installed_dists = installed_distributions()
        self._installed_dists_by_imports = installed_distributions_by_top_level_import_names(
            distributions=self._installed_dists.values()
        )
        self._requirements = _LocatableRequirements()
        self._cached_choices = dict()
        self._uncertain_requirements = collections.defaultdict(
            _LocatableRequirements
        )  # Multiple requirements for same import name.
        self._unknown_imports = collections.defaultdict(_Locations)
        self._unknown_imports_from_annotations = dict()
        self._unknown_dists_from_annotaions = collections.defaultdict(
            _Locations
        )

    def analyze_requirements(
        self,
        visit_doc_str=False,
        ignores=None,
        dists_filter=None,
        follow_symbolic_links=True,
        enable_requirement_annotations=False,
    ):
        imported_modules, annotations = parse_imports(
            self._project_root,
            visit_doc_str=visit_doc_str,
            exclude_patterns=ignores,
            followlinks=follow_symbolic_links,
            parse_requirement_annotations=enable_requirement_annotations,
        )

        importables = dict()
        tryimports = set()
        importlib.invalidate_caches()

        def _resolve(module: Module, from_annotation: bool):
            name = module.name
            if is_user_module(module, self._project_root):
                logger.debug(
                    "ignore import name from user module: %s", module.name
                )
                return
            is_stdlib, code_path = check_stdlib(name)
            if not is_stdlib:
                is_stdlib, code_path = check_stdlib(name.split('.')[0])
            if is_stdlib:
                logger.debug("ignore import name from stdlib: %s", module.name)
                return

            names = []
            special_name = '.'.join(name.split('.')[:2])
            # Flask extension.
            if name.startswith('flask.ext.'):
                names.append('flask')
                names.append('flask_' + name.split('.')[2])
            # Special cases..
            elif special_name in _special_import_names:
                names.append(special_name)
            # Other.
            elif '.' in name:
                names.append(name.split('.')[0])
            else:
                names.append(name)

            for name in names:
                if name in self._installed_dists_by_imports:
                    reqs = self._installed_dists_by_imports[name]
                    locs = _Locations.build_from(module.file, module.lineno)
                    reqs = self._maybe_filter_distributions_with_same_import_name(
                        name, locs, reqs, dists_filter
                    )
                    self._record_requirements(
                        name, locs, reqs, from_annotation
                    )
                else:
                    if code_path is not None:
                        importables[name] = code_path
                    if module.try_:
                        tryimports.add(name)
                    self._unknown_imports[name].add(module.file, module.lineno)
                    self._unknown_imports_from_annotations[name
                                                           ] = from_annotation

        for module in imported_modules:
            _resolve(module, False)
        for annotation in annotations:
            if annotation.top_level_import_name is not None:
                module = Module(
                    name=annotation.top_level_import_name,
                    file=annotation.file,
                    lineno=annotation.lineno,
                    try_=False
                )
                _resolve(module, True)
            elif annotation.distribution_name is not None:
                req = self._installed_dists.get(
                    canonicalize_name(annotation.distribution_name), None
                )
                if req is not None:
                    locs = _Locations.build_from(
                        annotation.file, annotation.lineno
                    )
                    self._record_requirements(None, locs, [req], True)
                else:
                    self._unknown_dists_from_annotaions[
                        annotation.distribution_name
                    ].add(annotation.file, annotation.lineno)

        resolved = set()
        for name, locs in self._unknown_imports.items():
            if name in tryimports:
                logger.debug(
                    "ignore import name with `try/except ImportError`: %s",
                    name
                )
                resolved.add(name)
            elif name in importables:
                # Handle special cases like distutils,
                # which is importable but it is not in top_level.txt.
                # Ref: https://docs.python.org/3/library/sys_path_init.html#pth-files
                code_path = importables[name]
                # Let's do a brute-force match..
                for req in self._installed_dists.values():
                    if req.contains_file(code_path):
                        # XXX: there is an issue if multiple distributions has the same path..
                        # reqs = self._maybe_filter_distributions_with_same_import_name( name, locs, reqs, dists_filter)
                        self._record_requirements(name, locs, [req], False)
                        logger.debug(
                            "the import name is importable(no top levels contains it): %s",
                            name
                        )
                        resolved.add(name)
                        break

        for name in resolved:
            del self._unknown_imports[name]

    def _record_requirements(
        self,
        import_name: Optional[str],
        locs: _Locations,
        reqs: List[FrozenRequirement],
        from_annotation: bool,
    ):
        requirements = self._requirements
        if import_name is not None and len(reqs) > 1:
            requirements = self._uncertain_requirements[import_name]
        for req in reqs:
            requirements.add_locs(req, locs, from_annotation=from_annotation)
            # FIXME: treat this the same as _unknown_imports
            self._unknown_dists_from_annotaions.pop(req.name, None)

    def search_unknown_imports_from_index(
        self,
        dists_filter=None,
        pypi_index_url=DEFAULT_PYPI_INDEX_URL,
        include_prereleases=False,
    ):
        found = set()

        async def _get_latest_version(
            pypi_dists: PyPIDistributions, dist_name: str
        ):
            try:
                latest = await pypi_dists.get_latest_distribution_version(
                    dist_name,
                    include_prereleases=include_prereleases,
                )
                return FrozenRequirement(dist_name, latest or '0.0.0')
            except Exception as e:
                logger.error('checking %s failed: %r', dist_name, e)

        async def _collect(
            pypi_dists: PyPIDistributions,
            module_name: Optional[str],
            locs: _Locations,
            dist_names: List[str],
            from_annotation: bool,
        ):
            reqs = await asyncio.gather(
                *[
                    _get_latest_version(pypi_dists, dist_name)
                    for dist_name in dist_names
                ],
                return_exceptions=True
            )
            self._record_requirements(module_name, locs, reqs, from_annotation)

        async def _main():
            async with PyPIDistributions(
                index_url=pypi_index_url
            ) as pypi_dists:
                tasks = []
                for name, locs in self._unknown_imports.items():
                    from_annotation = self._unknown_imports_from_annotations[
                        name]
                    logger.info(
                        'search distributions for import name %s ...', name
                    )
                    with database() as db:
                        distributions = db.query_distributions_by_top_level_module(
                            name
                        )
                    if distributions is None:
                        continue
                    distributions = self._maybe_filter_distributions_with_same_import_name(
                        name, locs, distributions, dists_filter
                    )
                    found.add(name)
                    tasks.append(
                        _collect(
                            pypi_dists,
                            name,
                            locs,
                            [dist.name for dist in distributions],
                            from_annotation=from_annotation,
                        )
                    )
                for name, locs in self._unknown_dists_from_annotaions.items():
                    tasks.append(
                        _collect(
                            pypi_dists,
                            None,
                            locs, [name],
                            from_annotation=True
                        )
                    )
                await asyncio.gather(*tasks, return_exceptions=True)

        asyncio.run(_main())

        for name in found:
            del self._unknown_imports[name]

    def write_requirements(
        self,
        stream: io.IOBase,
        with_ref_comments=False,
        comparison_specifier='==',
        with_banner=True,
        with_unknown_imports=False,
    ):
        package_root_parent = os.path.dirname(
            trim_suffix(self._project_root, os.sep)
        ) + os.sep

        if with_banner:
            stream.write(
                '# Automatically generated by https://github.com/damnever/pigar.\n\n'
            )
        for _, req in self._requirements.sorted_items():
            stream.write(
                req.format_as_text(
                    package_root_parent, with_ref_comments,
                    comparison_specifier
                )
            )

        if self._uncertain_requirements:
            stream.write(
                '\n# WARNING(pigar): some manual fixes might be required as pigar has detected duplicate requirements for the same import name (possibly for different submodules).\n'  # noqa: E501
            )
            uncertain_requirements = sorted(
                self._uncertain_requirements.items(),
                key=lambda item: item[0].lower()
            )
            for import_name, reqs in uncertain_requirements:
                stream.write(
                    f'# WARNING(pigar): the following duplicate requirements are for the import name: {import_name}\n'  # noqa: E501
                )
                with_ref_comments_once = with_ref_comments
                for _, req in reqs.sorted_items():
                    stream.write(
                        req.format_as_text(
                            package_root_parent, with_ref_comments_once,
                            comparison_specifier
                        )
                    )
                    with_ref_comments_once = False

        if with_unknown_imports and self._unknown_imports:
            stream.write(
                '\n# WARNING(pigar): pigar can not find requirements for the following import names.\n'
            )
            unknown_imports = sorted(
                self._unknown_imports.items(),
                key=lambda item: item[0].lower()
            )
            for import_name, locs in unknown_imports:
                if with_ref_comments:
                    comments = '\n#   '.join(locs.sorted_items())
                    stream.write(
                        f'# "{import_name}" referenced from:\n   {comments}\n'
                    )
                else:
                    stream.write(f'# {import_name}\n')

    def has_unknown_imports_or_uninstalled_annotations(self):
        return len(self._unknown_imports
                   ) > 0 or len(self._unknown_dists_from_annotaions) > 0

    def format_unknown_imports_or_uninstalled_annotations(self, stream):
        has_unknown_imports = len(self._unknown_imports) > 0
        for idx, (name, locs) in enumerate(self._unknown_imports.items()):
            if idx > 0:
                stream.write('\n')
            stream.write(
                '  {0} referenced from:\n    {1}'.format(
                    Color.YELLOW(name), '\n    '.join(locs.sorted_items())
                )
            )
        for idx, (name, locs) in enumerate(
            self._unknown_dists_from_annotaions.items()
        ):
            if idx > 0 or has_unknown_imports:
                stream.write('\n')
            stream.write(
                '  {0} annotated at:\n    {1}'.format(
                    Color.YELLOW(name), '\n    '.join(locs.sorted_items())
                )
            )

    def _maybe_filter_distributions_with_same_import_name(
        self, import_name, locations, distributions, dists_filter=None
    ):
        if dists_filter is None or len(distributions) <= 1:
            return distributions
        # We can use `functools.cache` in later versions of Python.
        existing = self._cached_choices.get(import_name, None)
        if existing is not None:
            return existing

        assert (hasattr(distributions[0], 'name'))

        best_match = None
        casefold_match = None
        contains = []
        for dist in distributions:
            if dist.name == import_name:
                best_match = dist
                break
            if dist.name.lower() == import_name.lower():
                casefold_match = dist
                break
            if dist.name.startswith(import_name
                                    ) or dist.name.endswith(import_name):
                contains.append(dist)
        if best_match is None and casefold_match is not None:
            best_match = casefold_match
        if best_match is None and len(contains) == 1:
            best_match = contains[0]
        choosed = dists_filter(
            import_name, locations, distributions, best_match
        )
        self._cached_choices[import_name] = choosed
        return choosed


class LocalRequirementWithLatestVersion(NamedTuple):
    name: str
    specifier: str
    local_version: str
    latest_version: str

    def asdict(self) -> Dict[str, Any]:
        return self._asdict()


async def check_requirements_latest_versions(
    requirement_files,
    pypi_index_url=DEFAULT_PYPI_INDEX_URL,
    include_prereleases=False,
) -> List[LocalRequirementWithLatestVersion]:
    installed_dists = installed_distributions()

    async def _collect(pypi_dists, req):
        local_version = ''
        latest_version = ''
        if req.has_name:
            if req.name in installed_dists:
                local_version = installed_dists[req.name].version
            try:
                latest_version = await pypi_dists.get_latest_distribution_version(
                    req.name,
                    include_prereleases=include_prereleases,
                )
            except Exception as e:
                logger.error(
                    'search latest version for %s failed: %r', req.name, e
                )
        return LocalRequirementWithLatestVersion(
            req.name, req.specifier, local_version or '', latest_version or ''
        )

    async with PyPIDistributions(index_url=pypi_index_url) as pypi_dists:
        tasks = []
        for file in requirement_files:
            logger.debug('checking requirements from %s', file)
            try:
                for req in parse_requirements(file):
                    tasks.append(_collect(pypi_dists, req))
            except PraseRequirementError as e:
                logger.error('parse %s failed: %r', file, e)
        res = await asyncio.gather(*tasks, return_exceptions=True)
    return sorted(res, key=lambda item: item.name.lower())


async def search_distributions_by_top_level_import_names(
    names: List[str],
    pypi_index_url=DEFAULT_PYPI_INDEX_URL,
    include_prereleases=False,
) -> Tuple[Dict[str, List[Tuple[str, str, str]]], List[str]]:
    results = collections.defaultdict(list)
    not_found = list()

    installed_dists = installed_distributions_by_top_level_import_names()

    async def _get_latest_version(pypi_dists, distribution, import_name):
        try:
            version = await pypi_dists.get_latest_distribution_version(
                distribution.name,
                include_prereleases=include_prereleases,
            )
            results[import_name].append(
                (distribution.name, version or '<unknown>', 'PyPI')
            )
        except Exception as e:
            logger.error('checking %s failed: %r', distribution.name, e)

    async def _collect(pypi_dists, import_name):
        logger.debug(
            'searching package distributions for "{0}" ...'.
            format(import_name)
        )
        # If exists in local environment, do not check on the PyPI.
        if import_name in installed_dists:
            for req in installed_dists[import_name]:
                results[import_name].append([req.name, req.version, 'local'])
        # Check information on the PyPI.
        else:
            with database() as db:
                distributions = db.query_distributions_by_top_level_module(
                    import_name
                )
            if distributions:
                await asyncio.gather(
                    *[
                        _get_latest_version(pypi_dists, dist, import_name)
                        for dist in distributions
                    ],
                    return_exceptions=True
                )
            else:
                not_found.append(import_name)

    async with PyPIDistributions(index_url=pypi_index_url) as pypi_dists:
        await asyncio.gather(
            *[_collect(pypi_dists, name) for name in names],
            return_exceptions=True
        )

    return results, not_found


def sync_distributions_index_from_pypi(
    index_url=DEFAULT_PYPI_INDEX_URL, concurrency=30
):
    print(Color.YELLOW('NOTE: this process may take a very LONG time!!!'))

    async def _main():
        async with PyPIDistributionsIndexSynchronizer(
            index_url=index_url,
            concurrency=concurrency,
        ) as synchronizer:
            try:
                await synchronizer.run()
                await synchronizer.wait()
            except (KeyboardInterrupt, SystemExit):
                await synchronizer.cancel()
                print(Color.BLUE('Operation canceled!'))
            except Exception as e:
                await synchronizer.cancel()
                logger.error("Unexpected error: ", exc_info=True)
                print(Color.BLUE('Operation aborted!'), e)
            else:
                print(Color.GREEN('Operation done!'))

    asyncio.run(_main())


@contextlib.contextmanager
def _exclude_sys_site_paths():
    origin_sys_path = sys.path.copy()
    site_paths = []
    for path in sys.path:
        if is_site_packages_path(path):
            site_paths.append(path)
    for path in site_paths:
        sys.path.remove(path)
    yield
    sys.path.clear()
    sys.path.extend(origin_sys_path)


@contextlib.contextmanager
def _prepend_sys_path(path: str):
    sys.path.insert(0, path)
    parent = os.path.dirname(path)
    if parent:
        sys.path.insert(1, parent)
    yield
    sys.path.remove(path)
    if parent:
        sys.path.remove(parent)


@contextlib.contextmanager
def _keep_sys_modules_clean():
    orignal_sys_modules = set(sys.modules.keys())
    yield
    for name in set(sys.modules.keys()) - orignal_sys_modules:
        sys.modules.pop(name)


# FIXME: this function is full of magic!
def is_user_module(module: Module, project_root: str):
    if module.name.startswith("."):
        return True

    root_module_name = module.name.split('.')[0]
    try:
        # FIXME(damnever): isolated environment!!
        spec = None
        with _exclude_sys_site_paths():
            with _prepend_sys_path(project_root):
                with _keep_sys_modules_clean():
                    for name in [module.name, root_module_name]:
                        try:
                            spec = importlib.util.find_spec(
                                name, os.path.dirname(module.file)
                            )
                            break
                        except Exception:
                            pass
        if spec.origin is None:
            return False
        return (
            spec.origin != module.file
            and is_commonpath([spec.origin, project_root], project_root)
        ) or root_module_name == os.path.basename(project_root)
    except Exception:
        return False


def _cache_check_stdlib(func):
    checked = dict()

    @functools.wraps(func)
    def _wrapper(name):
        if name not in checked:
            checked[name] = func(name)
        return checked[name]

    return _wrapper


@_cache_check_stdlib
def check_stdlib(name: str, _sys_lib_paths=determine_python_sys_lib_paths()):
    """Check whether it is stdlib module."""
    with _keep_sys_modules_clean():
        try:
            spec = importlib.util.find_spec(name)
        except ImportError:
            spec = None
        except Exception as e:
            logger.error('find_spec(%s) got unexpected error: %r', name, e)
            spec = None
        if spec is None:
            try:
                # __import__(name)
                importlib.import_module(name)
                spec = importlib.util.find_spec(name)
            except ImportError:
                return False, None
            except Exception as e:
                logger.error('find_spec(%s) got unexpected error: %r', name, e)
                return False, None

    module_path = spec.origin
    if module_path is None or not os.path.isabs(module_path):
        return True, None

    if is_site_packages_path(module_path):
        return False, module_path

    for sys_path in _sys_lib_paths:
        if is_commonpath([sys_path, module_path], sys_path):
            return True, None

    return False, module_path
