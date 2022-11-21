import unittest
import zipfile
import tarfile
import os
import shutil
import tempfile

from ..helpers import InMemoryOrDiskFile
from ..unpack import parse_top_levels


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
            zip_path, mode='w', compression=zipfile.ZIP_DEFLATED
        )
        try:
            zf.writestr('pigar-info/top_level.txt', 'pigar\npigar/tests')
        finally:
            zf.close()
        file = InMemoryOrDiskFile(zip_path, data=None, file_path=zip_path)
        self.assertListEqual(parse_top_levels(file), ['pigar', 'pigar.tests'])

    def test_tar(self):
        tar_path = os.path.join(self._tmp_path, 'pigar-1.1.tar.gz')
        tarf = tarfile.open(tar_path, 'w:gz')
        fpath = os.path.join(os.path.dirname(__file__), 'data/top_level.txt')
        try:
            tarf.add(fpath)
        finally:
            tarf.close()
        with open(tar_path, 'rb') as f:
            file = InMemoryOrDiskFile(tar_path, data=f.read(), file_path=None)
            self.assertListEqual(parse_top_levels(file), ['pigar.tests'])
