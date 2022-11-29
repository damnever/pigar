import os
import os.path as pathlib
import re
import codecs
import tempfile
from html.parser import HTMLParser
from urllib.parse import urljoin, quote, urlparse
from typing import Mapping, Set, List, NamedTuple, Optional, ValuesView
from html.parser import HTMLParser
from urllib.parse import urljoin
from collections import defaultdict
import concurrent.futures
import asyncio

from .log import logger
from .helpers import cmp_to_key, trim_prefix, trim_suffix, InMemoryOrDiskFile
from .unpack import parse_top_levels
from .db import database
from .version import version
from ._vendor.pip._internal.vcs.versioncontrol import RemoteNotFoundError, RemoteNotValidError, vcs
from ._vendor.pip._internal.exceptions import BadCommand, InstallationError

from distlib.database import DistributionPath, Distribution, EggInfoDistribution
from packaging.version import Version, InvalidVersion
from distlib.locators import SimpleScrapingLocator
from distlib.wheel import Wheel
from packaging.utils import canonicalize_name
import aiohttp

DEFAULT_PYPI_INDEX_URL = 'https://pypi.org/simple/'

# FIXME: dirty workaround..
# TODO: use custom configuration rather than hard-code mapping.
# Special distributions top level import name: Distribution name -> import names.
_hardcode_distributions_with_import_names = {
    "dogpile-cache": set("dogpile.cache", ),
    "dogpile-core": set("dogpile.core", ),
    "ruamel-yaml": set("ruamel.yaml", ),
}


def _all_hardcode_import_names():
    names = set()
    for _, import_names in _hardcode_distributions_with_import_names.items():
        names |= import_names
    return names


def _get_hardcode_distributions_import_names(name):
    return _hardcode_distributions_with_import_names.get(
        canonicalize_name(name), set()
    )


def _maybe_include_project_name_as_import_name(
    top_levels,
    project_name,
    _module_name_re=re.compile(r"^[a-zA-Z]+[a-zA-Z0-9_]*$")
):
    if not top_levels and _module_name_re.fullmatch(project_name) is not None:
        if isinstance(top_levels, set):
            top_levels.add(project_name)
        elif isinstance(top_levels, tuple):
            top_levels = (project_name, )
        else:
            top_levels = [project_name]
    return top_levels


class FrozenRequirement(object):
    """
    Modified version of:
    https://github.com/pypa/pip/blob/90f51db1a32592430f2e4f6fbb9efa7a3a249423/src/pip/_internal/operations/freeze.py#L219
    """

    def __init__(
        self,
        name: str,
        version: str,
        modules: List[str] = [],
        editable: bool = False,
        url: str = '',
        comments: List[str] = [],
        code_paths: Set[str] = set(),
    ):
        self.name = name
        self.version = version
        self.canonical_name = canonicalize_name(name)
        self.modules = modules
        self.editable = editable
        self.url = url
        self.comments = comments
        self.code_paths = code_paths

    @classmethod
    def from_dist(cls, dist):
        modules = set()
        editable = isinstance(dist, EggInfoDistribution)
        url = ''
        installed_files = []
        if editable:
            req, comments = _get_editable_info(dist)
            url = req
            top_level_file = pathlib.join(dist.path, 'top_level.txt')
            if os.path.exists(top_level_file):
                with open(top_level_file, 'rb') as f:
                    modules = set(f.read().decode('utf-8').splitlines())
            sources_file = os.path.join(dist.path, 'SOURCES.txt')
            if os.path.exists(sources_file):
                with codecs.open(
                    sources_file, mode='r', encoding='utf-8'
                ) as f:
                    installed_files = f.readlines()
        else:
            # read from RECORD file
            installed_files = [
                finfo[0] for finfo in dist.list_installed_files()
            ]
            comments = []
            modules = set(dist.modules)
            modules = _maybe_include_project_name_as_import_name(
                modules, dist.name
            )
            modules |= _get_hardcode_distributions_import_names(dist.name)

        dist_path = trim_suffix(dist.path, os.sep)
        root_dir = os.path.dirname(dist_path)
        dist_info_dir = os.path.basename(dist_path)
        code_paths = set()
        code_file_dir = os.pardir
        for file in installed_files:
            if not any(
                [
                    os.path.commonpath([code_file_dir, file]) ==
                    code_file_dir,  # Fast path to skip the same path prefix.
                    os.path.commonpath([dist_info_dir, file]) == dist_info_dir,
                    os.path.commonpath([os.pardir, file]) == os.pardir,
                    os.path.commonpath([os.curdir, file]) == os.curdir,
                    file.startswith('__')
                ]
            ):
                code_file_dir = trim_prefix(file, os.sep).split(os.sep)[0]
                code_path = os.path.join(root_dir, code_file_dir)
                if os.path.exists(code_path):
                    code_paths.add(code_path)

        return cls(
            dist.name,
            dist.version,
            list(modules),
            editable,
            url,
            comments=comments,
            code_paths=code_paths,
        )

    def contains_file(self, file):
        if not self.code_paths or not file:
            return False
        for code_path in self.code_paths:
            if code_path == os.path.commonpath([code_path, file]):
                return True
        return False

    def as_requirement(
        self, operator: str = '==', spaces_around_operator: str = ''
    ) -> str:
        req = ""
        if self.editable:
            req = f"-e {self.url}"
        else:
            req = f"{self.name}{spaces_around_operator}{operator}{spaces_around_operator}{self.version}"
        return "\n".join(list(self.comments) + [str(req)])

    def __str__(self) -> str:
        return self.as_requirement('==', '')

    def __repr__(self):
        modules = ' '.join(self.modules)
        code_paths = ' '.join(self.code_paths or [])
        return f'<{self.name} {self.version}  [{modules}]  [{code_paths}]>'


def installed_distributions_by_top_level_import_names(
    distributions: Optional[ValuesView[FrozenRequirement]] = None,
) -> Mapping[str, List[FrozenRequirement]]:
    """Mapping of top level import name to installed distributions."""
    mapping = defaultdict(list)
    distributions = distributions or installed_distributions().values()
    for req in distributions:
        for module in req.modules:
            mapping[module].append(req)

    return mapping


def installed_distributions() -> Mapping[str, FrozenRequirement]:
    mapping = dict()
    dist_path = DistributionPath(include_egg=True)
    for distribution in dist_path.get_distributions():
        req = FrozenRequirement.from_dist(distribution)
        logger.debug('found local distribution: %r', req)
        mapping[req.name] = req
    return mapping


def _format_dist_as_name_version(dist: Distribution):
    return "{}=={}".format(dist.name, dist.version)


class _EditableInfo(NamedTuple):
    requirement: str
    comments: List[str]


def _get_editable_info(dist: EggInfoDistribution) -> _EditableInfo:
    """
    Compute and return values (req, comments) for use in
    FrozenRequirement.from_dist().

    Ref: https://github.com/pypa/pip/blob/90f51db1a32592430f2e4f6fbb9efa7a3a249423/src/pip/_internal/operations/freeze.py#L153
    """
    editable_project_location = dist.path
    assert editable_project_location
    location = pathlib.normcase(pathlib.abspath(editable_project_location))
    if not pathlib.exists(location):
        return _EditableInfo(
            requirement="", comments=[f"# Editable not found: {dist}"]
        )

    vcs_backend = vcs.get_backend_for_dir(location)

    if vcs_backend is None:
        display = _format_dist_as_name_version(dist)
        logger.debug(
            'No VCS found for editable requirement "%s" in: %r',
            display,
            location,
        )
        return _EditableInfo(
            requirement=location,
            comments=[
                f"# Editable install with no version control ({display})"
            ],
        )

    vcs_name = type(vcs_backend).__name__

    try:
        req = vcs_backend.get_src_requirement(location, dist.name)
    except RemoteNotFoundError:
        display = _format_dist_as_name_version(dist)
        return _EditableInfo(
            requirement=location,
            comments=[
                f"# Editable {vcs_name} install with no remote ({display})"
            ],
        )
    except RemoteNotValidError as ex:
        display = _format_dist_as_name_version(dist)
        return _EditableInfo(
            requirement=location,
            comments=[
                f"# Editable {vcs_name} install ({display}) with either a deleted "
                f"local remote or invalid URI:",
                f"# '{ex.url}'",
            ],
        )
    except BadCommand:
        logger.warning(
            "cannot determine version of editable source in %s "
            "(%s command not found in path)",
            location,
            vcs_backend.name,
        )
        return _EditableInfo(requirement=location, comments=[])
    except InstallationError as exc:
        logger.warning(
            "Error when trying to get requirement for VCS system %s", exc
        )
    else:
        return _EditableInfo(requirement=req, comments=[])

    logger.warning("Could not determine repository location of %s", location)

    return _EditableInfo(
        requirement=location,
        comments=["## !! Could not determine repository location"],
    )


def _parse_urls_from_html(html, base_url, put):

    class _HrefParser(HTMLParser):

        def handle_starttag(self, tag, attrs):
            if tag == 'a':
                href = dict(attrs).get('href', None)
                if href is not None:
                    url = urljoin(base_url, href)
                    if url:
                        put(url)

    _HrefParser().feed(html)


def _parse_project_name_from_url(url):
    parsed = urlparse(url)
    return parsed.path.rstrip("/").split("/")[-1]


class PyPIDistributions(object):
    _ACCEPTABLE_EXT = ('.whl', '.egg', '.tar.gz', '.tar.bz2', '.zip')
    _HTTP_HEADERS = {
        'Accept': '*/*',
        'Accept-Encoding': 'gzip',
        'User-Agent': 'pigar/' + version,
    }

    def __init__(self, index_url=DEFAULT_PYPI_INDEX_URL):
        self._session = aiohttp.ClientSession()
        self._index_url = index_url

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, exc_traceback):
        await self.close()

    async def close(self):
        await self._session.close()

    async def get_latest_distribution_version(
        self, name, url=None, include_prereleases=False
    ):
        version, _ = await self.get_latest_distribution_info(
            name,
            url=url,
            include_prereleases=include_prereleases,
        )
        return version

    async def get_latest_distribution_info(
        self, name, url=None, include_prereleases=False
    ):
        if url is None:
            url = urljoin(self._index_url, quote(name) + '/')
        html = await self._download_text(url)
        download_urls = []
        _parse_urls_from_html(html, url, download_urls.append)
        return self._choose_distribution_url_with_latest_version(
            name,
            download_urls,
            include_prereleases=include_prereleases,
        )

    def _choose_distribution_url_with_latest_version(
        self, name, download_urls, include_prereleases=False
    ):
        dummy_locator = SimpleScrapingLocator('')
        versions = []
        for url in download_urls:
            path = urlparse(url).path
            if not path.endswith(self._ACCEPTABLE_EXT):
                continue

            version_str = None
            if path.endswith('.whl'):
                try:
                    wheel = Wheel(path)
                    version_str = wheel.version
                except Exception as e:
                    logger.debug('%s ignore: %r', name, e)
                    continue
            else:
                info = dummy_locator.convert_url_to_download_info(url, name)
                if info:
                    version_str = info.pop('version')
            if version_str is None:
                continue
            try:
                version = Version(version_str)
            except InvalidVersion as e:
                logger.debug('%s ignore: %r', name, e)
                continue

            if not include_prereleases and version.is_prerelease:
                continue
            versions.append((version, path, url))
        if len(versions) == 0:
            return None, None

        def _cmp_version(x, y):
            if x[0] < y[0]:
                return -1
            if x[0] > y[0]:
                return 1
            if x[1].endswith('.whl'):
                return 1
            if y[1].endswith('.whl'):
                return -1
            return 0

        versions.sort(key=cmp_to_key(_cmp_version), reverse=True)

        latest = versions[0]
        return str(latest[0]), latest[2]  # version, url

    async def get_latest_distribution(
        self,
        name,
        url=None,
        include_prereleases=True,
        tmp_download_dir=tempfile.gettempdir(),
    ):
        version, url = await self.get_latest_distribution_info(
            name,
            url,
            include_prereleases=include_prereleases,
        )
        if version is None:
            return (None, None, None)
        content = await self._download_raw(
            url, tmp_download_dir=tmp_download_dir
        )
        return (version, url, content)

    async def iter_all_distribution_urls(self, callback):
        html = await self._download_text(self._index_url, timeout=300)
        _parse_urls_from_html(html, self._index_url, callback)

    async def _download_text(self, url, timeout=30) -> str:
        async with self._session.get(
            url, headers=self._HTTP_HEADERS, timeout=timeout
        ) as resp:
            return await resp.text()

    async def _download_raw(
        self,
        url,
        timeout=30,
        read_in_mem_threshold=16777216,
        tmp_download_dir=tempfile.gettempdir()
    ) -> InMemoryOrDiskFile:
        async with self._session.get(
            url, headers=self._HTTP_HEADERS, timeout=timeout
        ) as resp:
            filename = os.path.basename(urlparse(url).path)
            if resp.content_length is not None and resp.content_length <= read_in_mem_threshold:
                data = await resp.read()
                return InMemoryOrDiskFile(filename, data=data, file_path=None)

            path = os.path.join(tmp_download_dir, filename)
            with open(path, 'wb') as f:
                while True:
                    block = await resp.content.readany()
                    if not block:
                        break
                    f.write(block)
            return InMemoryOrDiskFile(filename, data=None, file_path=path)


class PyPIDistributionsIndexSynchronizer(object):

    def __init__(
        self, index_url=DEFAULT_PYPI_INDEX_URL, concurrency=100, gc=False
    ):
        self._index_url = index_url
        self._concurrency = concurrency
        self._gc = gc  # TODO(damnever): delete distributions not existed anymore.
        self._pypi_distributions = PyPIDistributions()
        self._queue = asyncio.Queue()
        self._process_pool_executor = concurrent.futures.ProcessPoolExecutor()

        self._workers = []
        self._alive_worker_count = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, exc_traceback):
        await self._pypi_distributions.close()
        self._process_pool_executor.shutdown()

    async def run(self):
        logger.info('start synchronizing index from "%s" ...', self._index_url)
        await self._pypi_distributions.iter_all_distribution_urls(
            self._queue.put_nowait
        )
        size = self._queue.qsize()
        logger.debug(f'{size} distributions are ready in queue ...')

        self._alive_worker_count = self._concurrency
        for i in range(self._concurrency):
            worker = asyncio.create_task(self._worker(), name=f'worker-{i}')
            worker.add_done_callback(self._worker_done_callback)
            self._workers.append(worker)

    async def wait(self):
        await self._queue.join()
        await self.cancel()

    async def cancel(self):
        for w in self._workers:
            if not w.cancelled():
                w.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)

    def _worker_done_callback(self, task, *args, **kwargs):
        self._alive_worker_count -= 1
        if self._alive_worker_count > 0 or self._queue.empty():
            return

        logger.debug('all workers exited, empty the queue to avoid blocking..')
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except asyncio.QueueEmpty:
                break

    async def _worker(self):
        while True:
            project_url = await self._queue.get()
            try:
                await self._sync_project(project_url)
            finally:  # Avoid blocking on exceptions.
                self._queue.task_done()

    async def _sync_project(self, project_url):
        project_name = _parse_project_name_from_url(project_url)
        logger.info('processing distribution: %s', project_name)
        dist = None
        with database() as db:
            dist = db.query_distribution_with_top_level_modules(project_name)

        try:
            version, project_download_url = await self._pypi_distributions.get_latest_distribution_info(
                project_name,
                project_url,
                include_prereleases=False,
            )
            if version is None:
                logger.warn(
                    'distribution "%s" has no valid versions', project_name
                )
                return
            if dist is not None and Version(dist.version) >= Version(version):
                logger.info(
                    'distribution "%s" version is the latest: %s',
                    project_name, dist.version
                )
                return
            with tempfile.TemporaryDirectory() as tmp_download_dir:
                # FIXME(damnever): create temporary directory on demand.
                top_levels = await self._parse_top_levels(
                    project_name,
                    project_download_url,
                    tmp_download_dir,
                )
            if top_levels is None:
                return

            modules_to_add = set(top_levels or [])
            modules_to_delete = None
            if dist is not None:
                modules_to_delete = set(dist.modules) - modules_to_add
            with database() as db:
                db.store_distribution_with_top_level_modules(
                    project_name,
                    version,
                    modules_to_add,
                    modules_to_delete=modules_to_delete,
                )
        except aiohttp.ClientError as e:
            logger.error(
                (
                    'maybe distribution "%s" is no longer available'
                    ' or unparsable: %r'
                ), project_name, e
            )
        except Exception as e:
            logger.error(
                'process "%s" with unexpected error',
                project_name,
                exc_info=True,
            )
            raise e

    async def _parse_top_levels(
        self, project_name, project_download_url, tmp_download_dir
    ):
        dist_file = await self._pypi_distributions._download_raw(
            project_download_url, tmp_download_dir=tmp_download_dir
        )
        filename = urlparse(project_download_url).path

        event_loop = asyncio.get_event_loop()
        try:
            top_levels = await event_loop.run_in_executor(
                self._process_pool_executor, parse_top_levels, dist_file
            )
        except Exception:
            logger.error(
                'distribution %s(%s) may has invalid archive format:',
                project_name,
                filename,
                exc_info=True,
            )
            return None
        top_levels = _maybe_include_project_name_as_import_name(
            top_levels, project_name
        )

        x_import_names = _get_hardcode_distributions_import_names(project_name)
        if x_import_names:
            top_levels.extend(list(x_import_names))
        logger.debug(
            'distribution %s parsed top levels: %r', project_name, top_levels
        )
        return top_levels
