# -*- coding: utf-8 -*-

"""
 (c) 2017 - Copyright Red Hat Inc

 Authors:
   Patrick Uiterwijk <puiterwijk@redhat.com>

"""

from __future__ import unicode_literals, absolute_import

import logging
import os

from nose.plugins import Plugin

import perfrepo

log = logging.getLogger('nose.plugins.perfplugin')


class PerfPlugin(Plugin):
    """A plugin for Nose that reports back on the test performance."""
    name = 'pagureperf'

    def options(self, parser, env=None):
        if env is None:
            env = os.environ
        super(PerfPlugin, self).options(parser, env=env)

    def configure(self, options, conf):
        super(PerfPlugin, self).configure(options, conf)
        if not self.enabled:
            return

    def report(self, stream):
        stream.write('GIT PERFORMANCE TOTALS:\n')
        stream.write('\tWalks: %d\n' % perfrepo.TOTALS['walks'])
        stream.write('\tSteps: %d\n' % perfrepo.TOTALS['steps'])
