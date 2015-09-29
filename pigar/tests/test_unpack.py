# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import

import unittest
import zipfile
import tarfile
import os
import shutil
import tempfile

from ..unpack import top_level


class TopLevelTests(unittest.TestCase):

    def setUp(self):
        self._tmp_path = os.path.join(tempfile.gettempdir(), 'pigar/')
        os.mkdir(self._tmp_path)

    def tearDown(self):
        shutil.rmtree(self._tmp_path)

    def test_zip(self):
        # .whl and .egg both are .zip file.
        zip_path = os.path.join(self._tmp_path, 'pigar-1.1.zip')
        zf = zipfile.ZipFile(
            zip_path, mode='w', compression=zipfile.ZIP_DEFLATED)
        try:
            zf.writestr('pigar-info/top_level.txt', 'pigar\npigar/tests')
        finally:
            zf.close()
        with open(zip_path, 'rb') as f:
            self.assertListEqual(
                top_level(zip_path, f.read()), ['pigar', 'pigar.tests'])

    def test_tar(self):
        tar_path = os.path.join(self._tmp_path, 'pigar-1.1.tar.gz')
        tarf = tarfile.open(tar_path, 'w:gz')
        fpath = os.path.join(os.path.dirname(__file__), 'fake_top_level.txt')
        try:
            tarf.add(fpath)
        finally:
            tarf.close()
        with open(tar_path, 'rb') as f:
            self.assertListEqual(
                top_level(tar_path, f.read()), ['pigar.tests'])
