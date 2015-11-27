# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import

import json
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
from .utils import Color, compare_version, cmp_to_key


PYPI_URL = 'https://pypi.python.org/'
PKG_URL = 'https://pypi.python.org/pypi/{0}'
PKGS_URL = 'https://pypi.python.org/simple/'
PKG_INFO_URL = 'https://pypi.python.org/pypi/{0}/json'
ACCEPTABLE_EXT = ('.whl', '.egg', '.tar.gz', '.tar.bz2', '.zip')


def search_names(names, installed_pkgs):
    """Search package information by names(`import XXX`).
    """
    results = collections.defaultdict(list)
    not_found = list()
    for name in names:
        logger.info('Searching package name for "{0}" ...'.format(name))
        # If exists in local environment, do not check on the PyPI.
        if name in installed_pkgs:
            results[name].append(list(installed_pkgs[name]) + ['local'])
        # Check information on the PyPI.
        else:
            rows = None
            with database() as db:
                rows = db.query_all(name)
            if rows:
                for row in rows:
                    version = extract_pkg_version(row.package)
                    results[name].append((row.package, version, 'PyPI'))
            else:
                not_found.append(name)
    return results, not_found


def check_latest_version(package):
    """Check package latest version in PyPI."""
    version = extract_pkg_version(package)
    return version


def update_db():
    """Update database."""
    print(Color.BLUE('Starting update database (this will take a while)...'))
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
    print(Color.BLUE('Update database done!'))


def extract_pkg_info(pkg_name):
    """Extract package information from PyPI."""
    logger.info('Extracting information of package "{0}".'.format(pkg_name))
    data = _pkg_json_info(pkg_name)
    # Extracting names which can be imported.
    if not data or not data['urls']:
        logger.warning('Package "{0}" no longer available.'.format(pkg_name))
        return

    urls = [item['url'] for item in data['urls']
            if item['filename'].endswith(ACCEPTABLE_EXT)]
    # Has not satisfied compressed package.
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

    # Insert into database.
    with database() as db:
        db.insert_package(pkg_name)
        package = db.query_package(pkg_name)
        for top in top_levels:
            top = top or pkg_name  # empty top_level.txt
            db.insert_name(top, package.id)


def extract_pkg_version(pkg_name):
    """Extract package latest version from PyPI."""
    data = _pkg_json_info(pkg_name)
    if not data or not data['releases'] or not data['urls']:
        return 'unknown'
    latest = data['info'].get('version', None)
    if latest is None:
        latest = sorted(data['releases'], key=cmp_to_key(compare_version))
        latest = latest[-1]
    return latest


def _pkg_json_info(pkg_name):
    data = download(PKG_INFO_URL.format(pkg_name))
    if not data:  # 404
        return None
    data = json.loads(data.decode('utf-8'))
    return data


class Extractor(object):
    """Extractor use thread pool execute tasks.

    Can be used to extract /simple/<pkg_name> or /pypi/<pkg_name>/json.
    """

    def __init__(self, names, max_workers=None):
        self._names = names
        self._max_workers = max_workers or (multiprocessing.cpu_count() * 4)
        self._futures = dict()

    def extract(self, job):
        """Extract url by package name."""
        with concurrent.futures.ThreadPoolExecutor(
                max_workers=self._max_workers) as executor:
            for name in self._names:
                self._futures[executor.submit(job, name)] = name

            try:
                self.wait_complete()
            except KeyboardInterrupt:
                print(Color.BLUE('** Canceling ...^... Please wait **'))
                self.cancel()
                executor.shutdown()
                print(Color.BLUE('All tasks canceled!'))
            else:
                print(Color.BLUE('Extracting packages done!'))

    def wait_complete(self):
        """Wait for futures complete done."""
        for future in concurrent.futures.as_completed(self._futures.keys()):
            try:
                error = future.exception()
            except concurrent.futures.CancelledError:
                break
            name = self._futures[future]
            if error is not None:
                err_msg = 'Extracting "{0}", got: {1}'.format(name, error)
                logger.error(err_msg)

    def cancel(self):
        print("+" * 60)
        for future in self._futures:
            future.cancel()


# Fake headers, just in case.
_HEADERS = {
    'Accept': '*/*',
    'Accept-Encoding': 'gzip, deflate, sdch',
    'Accept-Language': 'en-US,en;q=0.8,zh-CN;q=0.6,zh;q=0.4',
    'User-Agent': ('Mozilla/5.0 (X11; Linux x86_64; rv:13.0) '
                   'AppleWebKit/537.36 (KHTML, like Gecko) '
                   'Chrome/44.0.2403.157 Safari/537.36'),
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

    class HrefParser(HTMLParser):
        def handle_starttag(self, tag, attrs):
            if tag == 'a':
                attrs = dict(attrs)
                if attrs.get('href', None):
                    names.append(attrs['href'])

    HrefParser().feed(html)
    return names
