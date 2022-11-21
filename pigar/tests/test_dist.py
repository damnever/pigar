import unittest
import os

from ..dist import _parse_urls_from_html


class HTMLParserTest(unittest.TestCase):

    def test_parse_urls_from_html(self):
        path = os.path.join(
            os.path.dirname(__file__), 'data/fake_simple_html.txt'
        )
        names = []
        with open(path) as f:
            _parse_urls_from_html(f.read(), 'http://o.x', names.append)
        expect = [
            "http://o.x/simple/a/",
            "http://o.x/simple/b/",
            "http://o.x/simple/c/",
            "http://o.x/d",
            "http://o.x/e",
            "http://o.x/f",
            "http://o.x/g",
        ]
        self.assertListEqual(names, expect)
