# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import

import collections


class Modules(dict):
    """Modules object will be used to store modules information."""

    def __init__(self):
        super(Modules, self).__init__()

    def remove(self, *names):
        for name in names:
            if name in self:
                self.pop(name)


class ImportedModules(Modules):

    def __init__(self):
        super(ImportedModules, self).__init__()

    def add(self, name, file, lineno):
        if name is not None and '.' in name and not name.startswith('.'):
            name = name.split('.')[0]
        if name not in self:
            self[name] = _Locations()
        self[name].add(file, lineno)

    def __or__(self, obj):
        for name, locations in obj.items():
            for file, linenos in locations.items():
                for lineno in linenos:
                    self.add(name, file, lineno)
        return self


class ReqsModules(Modules):

    _Detail = collections.namedtuple('Detail', ['version', 'comments'])

    def __init__(self):
        super(ReqsModules, self).__init__()

    def add(self, package, version, locations):
        if package in self:
            self[package].comments.extend(locations)
        else:
            self[package] = self._Detail(version, locations)


class _Locations(dict):
    """_Locations store code locations(file, linenos)."""

    def __init__(self):
        super(_Locations, self).__init__()

    def add(self, file, lineno):
        if file in self and lineno not in self[file]:
            self[file].append(lineno)
        else:
            self[file] = [lineno]

    def extend(self, obj):
        for file, linenos in obj.items():
            for lineno in linenos:
                self.add(file, lineno)

    def __iter__(self):
        for file, linenos in sorted(self.items()):
            yield ('{0}: {1}'.format(
                file, ','.join([str(n) for n in sorted(linenos)])))
