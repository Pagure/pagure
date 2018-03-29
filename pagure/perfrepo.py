# -*- coding: utf-8 -*-

"""
 (c) 2017 - Copyright Red Hat Inc

 Authors:
   Patrick Uiterwijk <puiterwijk@redhat.com>

"""

from __future__ import print_function, unicode_literals


import pprint
import os
import traceback
import types

import six
import pygit2
import _pygit2


real_pygit2_repository = pygit2.Repository

TOTALS = {'walks': 0,
          'steps': 0}
REQUESTS = []
STATS = {}


class PerfRepoMeta(type):
    def __new__(cls, name, parents, dct):
        # create a class_id if it's not specified
        if 'class_id' not in dct:
            dct['class_id'] = name.lower()

        # we need to call type.__new__ to complete the initialization
        return super(PerfRepoMeta, cls).__new__(cls, name, parents, dct)

    def __getattr__(cls, attr):
        real = getattr(real_pygit2_repository, attr)
        if type(real).__name__ in ['function', 'builtin_function_or_method']:
            def fake(*args, **kwargs):
                return real(*args, **kwargs)
            return fake
        else:
            return real


class FakeWalker(six.Iterator):
    def __init__(self, parent):
        self.parent = parent
        self.wid = STATS['counters']['walks']
        STATS['counters']['walks'] += 1

        STATS['walks'][self.wid] = {
            'steps': 0,
            'type': 'walker',
            'init': traceback.extract_stack(limit=3)[0],
            'iter': None}
        TOTALS['walks'] += 1

    def __getattr__(self, attr):
        return getattr(self.parent, attr)

    def __iter__(self):
        STATS['walks'][self.wid]['iter'] = traceback.extract_stack(limit=2)[0]

        return self

    def __next__(self):
        STATS['walks'][self.wid]['steps'] += 1
        TOTALS['steps'] += 1
        resp = next(iter(self.parent))
        return resp


class FakeDiffHunk(object):
    def __init__(self, parent):
        self.parent = parent

    def __getattr__(self, attr):
        print('Getting Fake Hunk %s' % attr)
        resp = getattr(self.parent, attr)
        print('Response: %s' % resp)
        return resp


class FakeDiffPatch(object):
    def __init__(self, parent):
        self.parent = parent

    def __getattr__(self, attr):
        if attr == 'hunks':
            return [FakeDiffHunk(h) for h in self.parent.hunks]
        return getattr(self.parent, attr)


class FakeDiffer(six.Iterator):
    def __init__(self, parent):
        self.parent = parent
        self.iter = None
        self.did = STATS['counters']['diffs']
        STATS['counters']['diffs'] += 1

        STATS['diffs'][self.did] = {
            'init': traceback.extract_stack(limit=3)[0],
            'steps': 0,
            'iter': None}

    def __getattr__(self, attr):
        return getattr(self.parent, attr)

    def __dir__(self):
        return dir(self.parent)

    def __iter__(self):
        STATS['diffs'][self.did]['iter'] = traceback.extract_stack(limit=2)[0]

        self.iter = iter(self.parent)
        return self

    def __next__(self):
        STATS['diffs'][self.did]['steps'] += 1
        resp = next(self.iter)
        if isinstance(resp, _pygit2.Patch):
            resp = FakeDiffPatch(resp)
        else:
            raise Exception('Unexpected %s returned from differ' % resp)
        return resp

    def __len__(self):
        return len(self.parent)


class PerfRepo(six.with_metaclass(PerfRepoMeta, six.Iterator)):
    """ An utility class allowing to go around pygit2's inability to be
    stable.

    """

    def __init__(self, path):
        STATS['repo_inits'].append((path, traceback.extract_stack(limit=2)[0]))
        STATS['counters']['inits'] += 1

        self.repo = real_pygit2_repository(path)
        self.iter = None

    def __getattr__(self, attr):
        real = getattr(self.repo, attr)
        if type(real) in [types.FunctionType,
                          types.BuiltinFunctionType,
                          types.BuiltinMethodType]:
            def fake(*args, **kwargs):
                resp = real(*args, **kwargs)
                if isinstance(resp, _pygit2.Walker):
                    resp = FakeWalker(resp)
                elif isinstance(resp, _pygit2.Diff):
                    resp = FakeDiffer(resp)
                return resp
            return fake
        elif isinstance(real, dict):
            real_getitem = real.__getitem__

            def fake_getitem(self, item):
                return real_getitem(item)
            real.__getitem__ = fake_getitem
            return real
        else:
            return real

    def __getitem__(self, item):
        return self.repo.__getitem__(item)

    def __contains__(self, item):
        return self.repo.__contains__(item)

    def __iter__(self):
        self.wid = STATS['counters']['walks']
        STATS['counters']['walks'] += 1
        STATS['walks'][self.wid] = {
            'steps': 0,
            'type': 'iter',
            'iter': traceback.extract_stack(limit=3)[0]}
        TOTALS['walks'] += 1

        self.iter = iter(self.repo)
        return self

    def __next__(self):
        STATS['walks'][self.wid]['steps'] += 1
        TOTALS['steps'] += 1
        return next(self.iter)


if six.PY2:
    # Disable perfrepo on PY3, it doesn't work
    pygit2.Repository = PerfRepo


def reset_stats():
    """Resets STATS to be clear for the next request."""
    global STATS
    STATS = {'walks': {},
             'diffs': {},
             'repo_inits': [],
             'counters': {'walks': 0,
                          'diffs': 0,
                          'inits': 0}}


# Make sure we start blank
reset_stats()


def print_stats(response):
    """Finalizes stats for the current request, and prints them possibly."""
    REQUESTS.append(STATS)
    if not os.environ.get('PAGURE_PERFREPO_VERBOSE'):
        return response

    print('Statistics:')
    pprint.pprint(STATS)

    return response
