# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import

import json
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
from .helpers import compare_version, cmp_to_key, binary_type

PYPI_URL = 'https://pypi.org'
PKG_URL = urljoin(PYPI_URL, '/pypi/{0}')
PKGS_URL = urljoin(PYPI_URL, '/simple/')
PKG_INFO_URL = urljoin(PYPI_URL, '/pypi/{0}/json')
ACCEPTABLE_EXT = ('.whl', '.egg', '.tar.gz', '.tar.bz2', '.zip')


class Downloader(object):
    _HEADERS = {
        'Accept':
        '*/*',
        'Accept-Encoding':
        'gzip',
        'Accept-Language':
        'en-US,en;q=0.8,zh-CN;q=0.6,zh;q=0.4',
        'User-Agent': (
            'Mozilla/5.0 (X11; Linux x86_64; rv:13.0) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/44.0.2403.157 Safari/537.36'
        ),
    }

    def __init__(self):
        self._session = requests.Session()

    def download(self, url, try_decode=True):
        # XXX(damnever): timeout?
        resp = self._session.get(url, headers=self._HEADERS)
        resp.raise_for_status()
        data = resp.content
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


class Updater(object):
    _CPU_NUM = multiprocessing.cpu_count()  # C*2+1? The bandwidth matters..

    def __init__(self, proc_num=_CPU_NUM):
        self._proc_num = proc_num
        if self._proc_num > 2:  # FIXME magic number
            self._proc_num = 2

        downloader = Downloader()
        index = downloader.download_index()
        downloader.close()
        with database():  # Create tables if necessary.
            pass
        # XXX(damnever): using the magic __new__???
        self._thread_updater = None
        if self._proc_num == 1:
            pkg_names = ThreadSharableQueue()
            _parse_indexed_packages(index, pkg_names.put)
            self._thread_updater = ThreadPoolUpdater(pkg_names)
        else:
            self._pkg_names = ProcessSharableQueue()
            t = threading.Thread(
                target=_parse_indexed_packages,
                args=(index, self._pkg_names.put)
            )
            t.daemon = True
            t.start()
            self._feed_thread = t
            self._procs = []

    def run(self):
        if self._thread_updater is not None:
            self._thread_updater.run()
            return

        for _ in range(self._proc_num):
            proc = multiprocessing.Process(
                target=self._proc_main,
                args=(self._pkg_names, ),
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

    def _proc_main(self, pkg_names, workernum=6):
        tupdater = ThreadPoolUpdater(pkg_names, workernum)
        tupdater.run()
        tupdater.wait()


class ThreadPoolUpdater(object):
    def __init__(self, pkg_names, workernum=6):
        if workernum > 6:
            workernum = 6
        elif workernum < 3:
            workernum = 3
        self._max_workers = workernum
        self._pkg_names = pkg_names
        self._futures = []

    def run(self):
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self._max_workers
        ) as executor:
            for _ in range(self._max_workers * 3):
                future = executor.submit(self.extract_and_update)
                self._futures.append(future)

    def wait(self):
        for future in concurrent.futures.as_completed(self._futures):
            try:
                error = future.exception()
            except concurrent.futures.CancelledError:
                break
            if error is not None:
                logger.error('unexpected error: {}'.format(error))

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
                    logger.info('processing package: %s', pkg_name)
                    pkg = dler.download_package(pkg_name)
                    top_levels = pkg.top_levels()
                    db.insert_package_with_imports(pkg_name, top_levels)
                except (requests.RequestException, KeyError) as e:
                    logger.error(
                        (
                            'maybe package "%s" is no longer available'
                            ' or non-standard: %r'
                        ), pkg_name, e
                    )
        except Empty:
            pass
        except Exception:
            logger.debug('thread exited:', exc_info=True)
            raise
        finally:
            dler.close()
            db.close()


def _parse_indexed_packages(html, put):
    """Extract data from html."""
    class PackageNameParser(HTMLParser):
        def handle_starttag(self, tag, attrs):
            if tag == 'a':
                attrs = dict(attrs)
                if attrs.get('href', None):
                    name = attrs['href'].strip('/').split('/')[-1]
                    put(name)

    PackageNameParser().feed(html)
