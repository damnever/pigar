# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import

import gzip
import json
import collections
import io
import threading
import multiprocessing
from multiprocessing import Queue as ProcessSharableQueue
try:  # py2
    from HTMLParser import HTMLParser
    from urlparse import urljoin
    from Queue import Empty, Queue as ThreadSharableQueue
except ImportError:  # py3
    from html.parser import HTMLParser
    from urllib.parse import urljoin
    from queue import Empty, Queue as ThreadSharableQueue

import concurrent.futures
import requests

from .db import database, Database
from .unpack import top_level
from .log import logger
from .utils import Color, compare_version, cmp_to_key, binary_type


PYPI_URL = 'https://pypi.org'
PKG_URL = urljoin(PYPI_URL, '/pypi/{0}')
PKGS_URL = urljoin(PYPI_URL, '/simple/')
PKG_INFO_URL = urljoin(PYPI_URL, '/pypi/{0}/json')
ACCEPTABLE_EXT = ('.whl', '.egg', '.tar.gz', '.tar.bz2', '.zip')


def search_names(names, installed_pkgs):
    """Search package information by names(`import XXX`).
    """
    dler = Downloader()
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
                    version = dler.download_package(row.package).version()
                    results[name].append((row.package, version, 'PyPI'))
            else:
                not_found.append(name)
    return results, not_found


def check_latest_version(package):
    """Check package latest version in PyPI."""
    return Downloader().download_package(package).version()


def update_db():
    """Update database."""
    print(Color.BLUE('Starting update database ...'))
    print(Color.YELLOW('The process will take a long time!!!'))
    logger.info('Crawling "{0}" ...'.format(PKGS_URL))
    try:
        updater = Updater()
    except Exception:
        logger.error("Fail to fetch all packages: ", exc_info=True)
        print(Color.RED('Operation aborted'))
        return

    try:
        updater.run()
        updater.wait()
    except (KeyboardInterrupt, SystemExit):
        # FIXME(damnever): the fucking signal..
        updater.cancel()
        print(Color.BLUE('Operation canceled!'))
    else:
        print(Color.BLUE('Operation done!'))


class Updater(object):
    _CPU_NUM = multiprocessing.cpu_count()  # C*2+1? The bandwidth matters..

    def __init__(self, proc_num=_CPU_NUM):
        self._proc_num = proc_num

        downloader = Downloader()
        index = downloader.download_index()
        downloader.close()

        threads_total = self._proc_num * 6
        if threads_total < 24:
            threads_total = 24
        self._threads_per_proc = threads_total // self._proc_num

        # XXX(damnever): using the magic __new__???
        self._thread_updater = None
        if proc_num == 1:
            pkg_names = ThreadSharableQueue()
            _extract_pkg_names(index, pkg_names.put)
            self._thread_updater = ThreadPoolUpdater(
                pkg_names, threads_total)
        else:
            self._pkg_names = ProcessSharableQueue()
            t = threading.Thread(
                target=_extract_pkg_names,
                args=(index, self._pkg_names.put)
            )
            t.daemon = True
            t.start()
            self._feed_thread = t
            self._procs = []

        with database():
            pass

    def run(self):
        if self._thread_updater is not None:
            self._thread_updater.run()
            return

        for _ in range(self._proc_num):
            proc = multiprocessing.Process(
                target=self._proc_main,
                args=(self._pkg_names, self._threads_per_proc),
            )
            proc.daemon = True
            proc.start()
            self._procs.append(proc)

    def wait(self):
        if self._thread_updater is not None:
            return self._thread_updater.wait()

        self._feed_thread.join()
        [proc.join() for proc in self._procs]

    def cancel(self):
        if self._thread_updater is not None:
            return self._thread_updater.cancel()

        [proc.terminate() for proc in self._procs]
        [proc.join(timeout=1) for proc in self._procs]

    def _proc_main(self, pkg_names, workernum):
        tupdater = ThreadPoolUpdater(pkg_names, workernum)
        tupdater.run()
        tupdater.wait()


class ThreadPoolUpdater(object):
    def __init__(self, pkg_names, workernum=24):
        self._max_workers = workernum
        self._pkg_names = pkg_names
        self._futures = []

    def run(self):
        with concurrent.futures.ThreadPoolExecutor(
                max_workers=self._max_workers) as executor:
            # Incase of unexpected error happens.
            for _ in range(self._max_workers*3):
                future = executor.submit(self.extract_and_update)
                self._futures.append(future)

    def wait(self):
        for future in concurrent.futures.as_completed(self._futures):
            try:
                error = future.exception()
            except concurrent.futures.CancelledError:
                break
            if error is not None:
                logger.error('Unexpected error: {}'.format(error))

    def cancel(self):
        for future in self._futures:
            future.cancel()

    def extract_and_update(self):
        dler = Downloader()
        db = Database()
        try:
            while 1:
                try:
                    pkg_name = self._pkg_names.get(block=False)
                    logger.info('Processing package: %s', pkg_name)
                    pkg = dler.download_package(pkg_name)
                    top_levels = pkg.top_levels()
                    db.insert_package_with_imports(pkg_name, top_levels)
                except (requests.RequestException, KeyError) as e:
                    logger.error(
                        ('Maybe package "%s" is no longer available'
                         ' or it is non-standard: %r'), pkg_name, e)
        except Empty:
            pass
        except Exception:
            logger.debug('Thread exited:', exc_info=True)
            raise
        finally:
            dler.close()
            db.close()


class Downloader(object):
    _HEADERS = {
        'Accept': '*/*',
        'Accept-Encoding': 'gzip',
        'Accept-Language': 'en-US,en;q=0.8,zh-CN;q=0.6,zh;q=0.4',
        'User-Agent': ('Mozilla/5.0 (X11; Linux x86_64; rv:13.0) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/44.0.2403.157 Safari/537.36'),
    }

    def __init__(self):
        self._session = requests.Session()

    def download(self, url, try_decode=True):
        # XXX(damnever): timeout?
        resp = self._session.get(url, headers=self._HEADERS)
        resp.raise_for_status()
        data = resp.content
        if 'gzip' == resp.headers.get('Content-Encoding'):
            try:
                with gzip.GzipFile(fileobj=io.BytesIO(data)) as gz:
                    data = gz.read()
            except (OSError, IOError):  # Not a gzip file
                pass
        if try_decode and isinstance(data, binary_type):
            data = data.decode('utf-8')
        return data

    def download_index(self):
        return self.download(PKGS_URL)

    def download_package(self, name):
        pkg_info = self.download(PKG_INFO_URL.format(name))
        return Package(name, json.loads(pkg_info), self)

    def close(self):
        self._session.close()


class Package(object):
    def __init__(self, name, pkg_info, downloader):
        self._name = name
        self._pkg_info = pkg_info
        self._downloader = downloader

    def version(self):
        info = self._pkg_info
        try:
            latest = info['info'].get('version', None)
            if latest is not None:
                return latest
            latest = sorted(info['releases'], key=cmp_to_key(compare_version))
            latest = latest[-1]
            return latest
        except KeyError:
            return 'unknown'

    def top_levels(self):
        # Extracting names which can be imported.
        url = None
        for item in self._pkg_info['urls']:
            if item['filename'].endswith(ACCEPTABLE_EXT):
                url = item['url']
                break
        if url is None:
            return []
        pkg = self._downloader.download(url, try_decode=False)
        try:
            return top_level(url, pkg)
        except Exception:
            return []


def _extract_pkg_names(html, put):
    """Extract data from html."""
    class PackageNameParser(HTMLParser):
        def handle_starttag(self, tag, attrs):
            if tag == 'a':
                attrs = dict(attrs)
                if attrs.get('href', None):
                    name = attrs['href'].strip('/').split('/')[-1]
                    put(name)

    PackageNameParser().feed(html)
