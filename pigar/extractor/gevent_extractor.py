# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import

import time

import greenlet
from gevent.pool import Pool

from .extractor import BaseExtractor


class GeventExtractor(BaseExtractor):

    def __init__(self, names, max_workers=1000):
        super(self.__class__, self).__init__(names, max_workers)
        self._pool = Pool(self._max_workers)
        self._exited_greenlets = 0

    def extract(self, job):
        job = self._job_wrapper(job)
        for name in self._names:
            if self._pool.full():
                time.sleep(0.01)
            else:
                self._pool.spawn(job, name)

    def _job_wrapper(self, job):
        def _job(name):
            result = None
            try:
                result = job(name)
            except greenlet.GreenletExit:
                self._exited_greenlets += 1
            except Exception:
                e = sys.exc_info()[1]
                logger.error('Extracting "{0}", got: {1}'.format(name, e))
            return result
        return _job

    def wait_complete(self):
        self._pool.join()

    def shutdown(self):
        self._pool.kill()

    def final(self):
        count = self._exited_greenlets
        if count != 0:
            print(
                Color.YELLOW(
                    '** {0} running job exited with exception.'.format(count)
                )
            )


