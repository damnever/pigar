import unittest
import os

from ..dist import _parse_urls_from_html, _URLElement


class HTMLParserTest(unittest.TestCase):

    def test_parse_urls_from_html(self):
        path = os.path.join(
            os.path.dirname(__file__), 'data/fake_simple_html.txt'
        )
        names = []
        with open(path) as f:
            _parse_urls_from_html(f.read(), 'http://o.x', names.append)
        expect = [
            _URLElement(name="a", url="http://o.x/simple/a/"),
            _URLElement(name="b", url="http://o.x/simple/b/"),
            _URLElement(name="c", url="http://o.x/simple/c/"),
            _URLElement(name="D", url="http://o.x/d"),
            _URLElement(name="E1", url="http://o.x/e"),
            _URLElement(name="f", url="http://o.x/f"),
            _URLElement(name="g", url="http://o.x/g"),
        ]
        self.assertEqual(len(expect), len(names))
        for i, e in enumerate(expect):
            self.assertEqual(str(e), str(names[i]))
