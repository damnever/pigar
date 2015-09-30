# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import

import sys
import json
import signal
import collections
import multiprocessing
try:  # py2
    from urllib2 import urlopen, Request, URLError, HTTPError
    from HTMLParser import HTMLParser
except ImportError:  # py3
    from urllib.request import urlopen, Request
    from urllib.error import URLError, HTTPError
    from html.parser import HTMLParser

import concurrent.futures

from .db import database
from .unpack import top_level, unpack_html
from .log import logger


PYPI_URL = 'https://pypi.python.org/'
PKG_URL = 'https://pypi.python.org/pypi/{0}'
PKGS_URL = 'https://pypi.python.org/simple/'
PKG_INFO_URL = 'https://pypi.python.org/pypi/{0}/json'
ACCEPTABLE_EXT = ('.whl', '.egg', '.tar.gz', '.tar.bz2', '.zip')


def search_names(names, installed_pkgs):
    """Search package information by names(import in Python code).
    """
    logger.info('Starting search names ...')
    results = collections.defaultdict(list)
    not_found = list()
    for name in names:
        logger.info('Searching package name for "{0}" ...'.format(name))
        # If exists in local environment, do not check in pypi.
        if name in installed_pkgs:
            results[name].append(list(installed_pkgs[name]) + ['local'])
        # Check information in pypi.
        else:
            rows = None
            with database() as db:
                rows = db.query_all(name)
            if rows:
                for row in rows:
                    version = extract_pkg_info(row.package, True)
                    results[name].append((row.package, version, 'pypi'))
            else:
                not_found.append(name)
    return results, not_found


def check_latest_version(package):
    """Check package latest version in pypi."""
    version = extract_pkg_info(package, True)
    return version


def update_db():
    """Update database."""
    logger.info('Starting update database (this will take awhile)...')
    logger.info('Crawling "{0}" ...'.format(PKGS_URL))
    data = download(PKGS_URL)
    if not data:
        logger.error('Operation abort ...')
        return

    logger.info('Extracting all packages ...')
    pkg_names = _extract_html(unpack_html(data))
    with database() as db:
        ignore_pkgs = db.query_package(None)
        pkg_names = list(set(pkg_names) - set(ignore_pkgs))
    extractor = Extractor(pkg_names)
    extractor.extract(extract_pkg_info)


def extract_pkg_info(pkg_name, just_version=False):
    """Extract package information from PYPI."""
    data = download(PKG_INFO_URL.format(pkg_name))
    if not data:  # 404
        logger.warning('Package "{0}" no longer available.'.format(pkg_name))
        return
    data = json.loads(data.decode('utf-8'))

    # If `just_version` is True, just return version.
    if just_version:
        if not data['releases'] or not data['urls']:
            return 'unknown'
        latest = data['info'].get('version', None)
        if not latest:
            latest = max(
                [[int(n if n.isdigit() else [c for c in n if c.isdigit()][0])
                  for n in v.split('.')] for v in data['releases'].keys()])
            latest = '.'.join(str(n) for n in latest)
        return latest

    # If `just_version` is False,
    # need extracting names which can be imported.
    if not data or not data['urls']:
        logger.warning('Package "{0}" no longer available.'.format(pkg_name))
        return
    urls = [item['url'] for item in data['urls']
            if item['filename'].endswith(ACCEPTABLE_EXT)]
    # Does not has satisfied compressed package.
    if not urls:
        logger.warning('Package "{0}" can not unpack.'.format(pkg_name))
        return
    url = urls[0]

    top_levels = top_level(url, download(url))
    # Maybe package is a project, not importable...
    if not top_levels:
        logger.warning(
            'Maybe package "{0}" is not importable.'.format(pkg_name))
        return

    with database() as db:
        db.insert_package(pkg_name)
        package = db.query_package(pkg_name)
        for top in top_levels:
            top = top or pkg_name  # empty top_level.txt
            db.insert_name(top, package.id)


class Extractor(object):
    """Extractor use thread pool execute tasks.

    Can be used to extract /simple/<pkg_name> or /pypi/<pkg_name>/json.
    """

    def __init__(self, names, max_workers=None):
        self._names = names
        self._max_workers = max_workers or (multiprocessing.cpu_count() * 5)
        self._futures = dict()
        self._canceled = False

        # Register signal SIGINT and ...
        if sys.stdin.isatty():
            signal.signal(signal.SIGINT, self._signal_stop)
        for sig in (signal.SIGABRT, signal.SIGTERM):
            signal.signal(sig, self._signal_stop)

    def extract(self, job):
        """Extract url by package name."""
        with concurrent.futures.ThreadPoolExecutor(
                max_workers=self._max_workers) as executor:
            for name in self._names:
                self._futures[executor.submit(job, name)] = name

            self.wait_complete()
            if self._canceled:
                logger.warning('** Canceling ...^... Please wait **')
                executor.shutdown()
        logger.info('Extracting packages done')

    def wait_complete(self):
        """Wait for futures complete done."""
        for future in concurrent.futures.as_completed(self._futures.keys()):
            try:
                error = future.exception()
            except concurrent.futures.CancelledError:
                break
            name = self._futures[future]
            if error is None:
                logger.info('Extracting "{0}" done'.format(name))
            else:
                err_msg = 'Extracting "{0}", got: {1}'.format(name, error)
                logger.error(err_msg)

    def cancel(self):
        for future in self._futures:
            future.cancel()
        self._canceled = True

    def _signal_stop(self, signum, frame):
        logger.warning('Received signal {0}, stoping ...'.format(signum))
        self.cancel()


# Fake headers, just in case.
_HEADERS = {
    'Accept': '*/*',
    'Accept-Encoding': 'gzip, deflate, sdch',
    'Accept-Language': 'en-US,en;q=0.8,zh-CN;q=0.6,zh;q=0.4',
    'User-Agent': ('Mozilla/5.0 (X11; Linux x86_64; rv:13.0) AppleWebKit/537.36'
                   ' (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36'),
}


def download(url, headers=_HEADERS):
    """Download data from url."""
    data = ''
    try:
        f = urlopen(Request(url, headers=headers))
    except HTTPError as e:
        logger.error('Crawling "{0}", got: {1} {2}'.format(
            url, e.code, e.reason))
    except URLError as e:
        logger.error('Crawling "{0}", got: {1}'.format(url, e.reason))
    else:
        data = f.read()
        f.close()
    return data


def _extract_html(html):
    """Extract data from html."""
    names = list()

    class MyParser(HTMLParser):
        _link = None

        def handle_starttag(self, tag, attrs):
            if tag == 'a':
                attrs = dict(attrs)
                if attrs.get('href', None):
                    names.append(attrs['href'])

    MyParser().feed(html)
    return names
