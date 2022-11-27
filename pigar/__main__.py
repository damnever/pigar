import os
import os.path
import sys
import io
import codecs
import glob
import asyncio
import multiprocessing

from .version import version
from .log import enable_pretty_logging, logger
from .helpers import Color, print_table, lines_diff
from .parser import DEFAULT_GLOB_EXCLUDE_PATTERNS
from .core import (
    RequirementsAnalyzer,
    check_requirements_latest_versions,
    search_distributions_by_top_level_import_names,
    sync_distributions_index_from_pypi,
)
from .dist import DEFAULT_PYPI_INDEX_URL

import click


# Ref: https://click.palletsprojects.com/en/5.x/advanced/
class AliasedGroup(click.Group):

    def get_command(self, ctx, cmd_name):
        rv = click.Group.get_command(self, ctx, cmd_name)
        if rv is not None:
            return rv
        matches = [
            x for x in self.list_commands(ctx) if x.startswith(cmd_name)
        ]
        if not matches:
            return None
        elif len(matches) == 1:
            return click.Group.get_command(self, ctx, matches[0])
        ctx.fail(
            'Too commands has the same prefix: %s' %
            ', '.join(sorted(matches))
        )


def _click_prompt_choose_multiple_or_all(choices):

    def _value_proc(input):
        input = input.strip()
        if input == '*':
            return choices

        vs = [a.strip() for a in input.split(',')]
        for v in vs:
            if v not in choices:
                raise click.BadParameter(f'choice "{v}" not found')
        return vs

    return _value_proc


@click.group(
    cls=AliasedGroup,
    context_settings=dict(
        help_option_names=['-h', '--help'],
        max_content_width=120,
    ),
)
@click.version_option(version=version)
@click.option(
    '-l',
    '--log-level',
    'log_level',
    default='WARNING',
    show_default=True,
    help='Show given level log messages.',
    type=click.Choice(['ERROR', 'WARNING', 'INFO', 'DEBUG']),
)
def cli(log_level):
    '''A tool to generate requirements.txt for your Python project,
    and more than that.

    NOTE that pigar is not a package/dependency management tool.
    '''
    enable_pretty_logging(log_level)


@click.command(name='gohome')
def gohome():
    '''Go to the project home page to report a BUG or find more information.'''
    click.launch('https://github.com/damnever/pigar')


@click.command(name='generate')
@click.option(
    '-f',
    '--requirement-file',
    'requirement_file',
    default='requirements.txt',
    show_default=True,
    type=click.Path(dir_okay=False),
    help='The path to requirement file.',
)
@click.option(
    '--with-referenced-comments',
    'with_referenced_comments',
    default=False,
    show_default=True,
    is_flag=True,
    help='Add comments to list all files which import the requirement.',
)
@click.option(
    '-c',
    '--comparison-specifier',
    'comparison_specifier',
    default='==',
    show_default=True,
    type=click.Choice(['==', '~=', '>=', '>']),
    help='Part of version specifier, e.g. `abc==1.0`(see PEP 440 for details).',
)
@click.option(
    '--show-differences/--dont-show-differences',
    'show_differences',
    default=True,
    help=
    'Whether to show differences when the requirements file is overwritten.',
)
@click.option(
    '--visit-doc-string',
    'visit_doc_string',
    default=False,
    is_flag=True,
    help='Consider doctest in doc string when analyzing import statements.',
)
@click.option(
    '-e',
    '--exclude-glob',
    'exclude_glob',
    default=list(DEFAULT_GLOB_EXCLUDE_PATTERNS),
    show_default=True,
    multiple=True,
    type=str,
    help=
    'Exclude files and directories for searching that match the given glob.',
)
@click.option(
    '--follow-symbolic-links/--dont-follow-symbolic-links',
    'follow_symbolic_links',
    default=True,
    show_default=True,
    help='Whether to follow all symbolic links to the final target.',
)
@click.option(
    '--dry-run',
    'dry_run',
    default=False,
    is_flag=True,
    help=
    'Don\'t actually write a requirements file, just print the file content.',
)
@click.option(
    '-i',
    '--index-url',
    'index_url',
    default=DEFAULT_PYPI_INDEX_URL,
    show_default=True,
    help=
    'Base URL of the Python Package Index, this should point to a repository compliant with PEP 503 (the simple repository API)',
)
@click.option(
    '--include-prereleases',
    'include_prereleases',
    default=False,
    show_default=True,
    is_flag=True,
    help='Include pre-release and development versions.',
)
@click.option(
    '--question-answer',
    'question_answer',
    default='ask',
    show_default=True,
    type=click.Choice(['ask', 'yes', 'no']),
    help=
    'Whether to answer all possible questions with yes or no, otherwise manual confirmation is required.'
)
@click.option(
    '--auto-select',
    'auto_select',
    default=False,
    show_default=True,
    is_flag=True,
    help=
    'When multiple package/distributions are found for the same module, select the best matched one or all of them automatically, otherwise manual interaction is required.'
)
@click.argument(
    'project_path',
    default=os.curdir,
    type=click.Path(file_okay=False, exists=True)
)
def generate(
    requirement_file, with_referenced_comments, comparison_specifier,
    show_differences, visit_doc_string, exclude_glob, follow_symbolic_links,
    dry_run, index_url, include_prereleases, question_answer, auto_select,
    project_path
):
    '''Generate requirements.txt for the given Python project.'''
    requirement_file = os.path.abspath(requirement_file)
    project_path = os.path.abspath(project_path)

    def _dists_filter(import_name, locations, distributions, best_match):
        if auto_select:
            if best_match:
                return [best_match]
            return distributions

        dists_mapping = {dist.name: dist for dist in distributions}
        dist_names = list(dists_mapping.keys())
        msg = 'Please select one or more packages from the below list for the module '
        msg += Color.YELLOW(f'"{import_name}"')
        msg += f' (input * to select all, multiple values can be sperated by ",")\n'
        dist_names_msg = ', '.join(dist_names)
        msg += Color.YELLOW(f'[{dist_names_msg}]\n')
        if best_match is not None:
            msg += f'(the best match may be '
            msg += Color.YELLOW(f'"{best_match.name}"')
            msg += ')'
        choosed = click.prompt(
            msg,
            type=click.Choice(dist_names),
            show_choices=False,
            value_proc=_click_prompt_choose_multiple_or_all(dist_names),
        )
        return [dists_mapping[i] for i in choosed]

    analyzer = RequirementsAnalyzer(project_path)
    analyzer.analyze_requirements(
        visit_doc_str=visit_doc_string,
        ignores=exclude_glob,
        dists_filter=_dists_filter,
        follow_symbolic_links=follow_symbolic_links
    )
    if analyzer.has_unknown_imports():
        msgbuf = io.StringIO()
        yes = False
        if question_answer == 'ask':
            msgbuf.write(
                Color.RED('The following module(s) are not found yet:\n')
            )
            analyzer.format_unknown_imports(msgbuf)
            msgbuf.write('\n')
            msgbuf.write(
                Color.RED(
                    (
                        'Some of them may be not installed in the local environment.\n'
                        'Try to search them on PyPI for further analysis?'
                    )
                )
            )
            yes = click.confirm(msgbuf.getvalue(), default=False)
            # msgbuf.close()
        else:
            yes = question_answer == 'yes'

        if yes:
            analyzer.search_unknown_imports_from_index(
                dists_filter=_dists_filter,
                pypi_index_url=index_url,
                include_prereleases=include_prereleases,
            )
            if analyzer.has_unknown_imports():
                print(Color.RED('These module(s) are still not found:'))
                analyzer.format_unknown_imports(sys.stdout)
                sys.stdout.flush()
                # print(Color.RED('Maybe or you need update database.'))

    if dry_run:
        buf = io.StringIO()
        analyzer.write_requirements(
            buf,
            with_ref_comments=with_referenced_comments,
            comparison_specifier=comparison_specifier,
            with_banner=False,
            with_unknown_imports=False
        )
        # buf.close()
        print(Color.GREEN('\nGenerated requirements are as follows:'))
        print(buf.getvalue(), end='')
        return

    def _read_requirement_file(path):
        if not os.path.isfile(path):
            return None
        with codecs.open(path, 'rb', 'utf-8') as f:
            return f.readlines()

    old_requirement_file_content = _read_requirement_file(requirement_file)

    tmp_requirement_file = requirement_file + ".tmp"
    try:
        with open(tmp_requirement_file, 'w+') as f:
            analyzer.write_requirements(
                f,
                with_ref_comments=with_referenced_comments,
                comparison_specifier=comparison_specifier,
                with_banner=True,
                with_unknown_imports=False
            )
        os.rename(tmp_requirement_file, requirement_file)
    finally:
        try:
            os.remove(tmp_requirement_file)
        except FileNotFoundError:
            pass

    if show_differences:
        msg = 'Requirements file has been overwritten, '
        if old_requirement_file_content is not None:
            new_requirement_file_content = _read_requirement_file(
                requirement_file
            )
            is_diff, diffs = lines_diff(
                old_requirement_file_content, new_requirement_file_content
            )
            if is_diff:
                msg += 'here is the difference:'
                print(
                    '{0}\n{1}'.format(Color.YELLOW(msg), ''.join(diffs)),
                    end=''
                )
        else:
            msg += 'no difference.'
            print(Color.YELLOW(msg))

    print(Color.GREEN(f'Requirements has been written to {requirement_file}.'))


@click.command(name='check')
@click.option(
    '-f',
    '--requirement-file',
    'requirement_file',
    default='',
    type=click.Path(dir_okay=False),
    help='The path to requirement file.',
)
@click.option(
    '-i',
    '--index-url',
    'index_url',
    default=DEFAULT_PYPI_INDEX_URL,
    show_default=True,
    help=
    'Base URL of the Python Package Index, this should point to a repository compliant with PEP 503 (the simple repository API)',
)
@click.option(
    '--include-prereleases',
    'include_prereleases',
    default=False,
    show_default=True,
    is_flag=True,
    help='Include pre-release and development versions.',
)
def check(requirement_file, index_url, include_prereleases):
    '''Check latest versions for packages/distributions from requirements.txt.'''
    files = []
    cwd = os.getcwd()
    if not requirement_file:
        logger.debug('searching requirements file under {0} ...'.format(cwd))
        files.extend(glob.glob(os.path.join(cwd, '*requirements.txt')))
    else:
        requirement_file = os.path.abspath(requirement_file)
        files.append(requirement_file)
    if not files:
        print(
            Color.YELLOW(
                'Requirements file not found, use `pigar generate` to generate one.'
            )
        )
        return

    res = asyncio.run(
        check_requirements_latest_versions(
            files,
            pypi_index_url=index_url,
            include_prereleases=include_prereleases
        )
    )
    print_table(res, headers=['DISTRIBUTION', 'SPEC', 'LOCAL', 'LATEST'])


@click.command(name='search')
@click.option(
    '-i',
    '--index-url',
    'index_url',
    default=DEFAULT_PYPI_INDEX_URL,
    show_default=True,
    help=
    'Base URL of the Python Package Index, this should point to a repository compliant with PEP 503 (the simple repository API)',
)
@click.option(
    '--include-prereleases',
    'include_prereleases',
    default=False,
    show_default=True,
    is_flag=True,
    help='Include pre-release and development versions.',
)
@click.argument('names', nargs=-1, type=str)
def search(names, index_url, include_prereleases):
    '''Search packages/distributions by the top level import/module names'''
    results, not_found = asyncio.run(
        search_distributions_by_top_level_import_names(
            names,
            pypi_index_url=index_url,
            include_prereleases=include_prereleases,
        )
    )
    for name in results:
        print(
            'Found package distribution(s) for import name "{0}":'.format(
                Color.GREEN(name)
            )
        )
        print_table(
            results[name], headers=['DISTRIBUTION', 'VERSION', 'WHERE']
        )
    if not_found:
        msg = '"{0}" not found.'.format(Color.RED(', '.join(not_found)))
        print(Color.YELLOW(msg))


@click.group(name='indexdb')
def indexdb():
    '''Index database related operations.'''
    pass


@indexdb.command(name='sync')
@click.option(
    '-i',
    '--index-url',
    'index_url',
    default=DEFAULT_PYPI_INDEX_URL,
    show_default=True,
    help=
    'Base URL of the Python Package Index, this should point to a repository compliant with PEP 503 (the simple repository API)',
)
@click.option(
    '-c',
    '--concurrency',
    'concurrency',
    default=multiprocessing.cpu_count() * 2 + 1,
    type=int,
    show_default=True,
    help='The number of workers to process distributions concurrently.',
)
def indexdb_sync(index_url, concurrency):
    '''Synchronize the local index database with distributions' metadata on PyPI.'''
    # TODO: garbage collection.
    sync_distributions_index_from_pypi(
        index_url=index_url, concurrency=concurrency
    )


cli.add_command(gohome)
cli.add_command(generate)
cli.add_command(check)
cli.add_command(search)
cli.add_command(indexdb)


def main():
    cli()


if __name__ == '__main__':
    main()
