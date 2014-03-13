#!/usr/bin/env python
import argparse
import logging
import os

from pyinotify import WatchManager, Notifier, EventsCodes, ProcessEvent
import sys

from pym.cli import Cli
from pym.exc import SassError
from pym.lib import compile_sass_file


class Runner(Cli):

    def __init__(self):
        super().__init__()
        self.in1 = None
        self.in2 = None
        self.out1 = None
        self.out2 = None

    def init_app(self, args, lgg=None, rc=None, rc_key=None, setup_logging=True):
        super().init_app(args, lgg, rc, rc_key, setup_logging)
        rc = self.rc
        self.in1 = rc.g('sass.in', None)
        if not self.in1:
            raise SassError('Configuration error: sass.in is undefined.')
        self.out1 = rc.g('sass.out', None)
        if not self.out1:
            raise SassError('Configuration error: sass.out is undefined.')
        self.in2 = rc.g('sass.in2', None)
        self.out2 = rc.g('sass.out2', None)
        if self.in2 and not self.out2:
            raise SassError('Configuration error: sass.out2 is undefined.')


class Watcher(ProcessEvent):

    def __init__(self, lgg, in1, out1, in2, out2):
        super().__init__()
        self.lgg = lgg
        self.in1 = in1
        self.in2 = in2
        self.out1 = out1
        self.out2 = out2

    def process_IN_MODIFY(self, evt):
        try:
            compile_sass_file(self.in1, self.out1, 'nested')
        except SassError as exc:
            self.lgg.exception(exc)
        else:
            self.lgg.debug("Compiled SASS '{}' to '{}'".format(self.in1, self.out1))
        if self.in2:
            try:
                compile_sass_file(self.in2, self.out2, 'nested')
            except SassError as exc:
                self.lgg.exception(exc)
            else:
                self.lgg.debug("Compiled SASS '{}' to '{}'".format(self.in2, self.out2))


def main():
    me = os.path.splitext(os.path.basename(sys.argv[0]))[0]
    lgg = logging.getLogger('cli.' + me)

    runner = Runner()

    # Main parser
    parser = argparse.ArgumentParser(description="""Create test data.""")
    runner.add_parser_args(parser, which=[('config', True), ('locale', False)])

    args = parser.parse_args()

    runner.init_app(args, lgg=lgg)
    watcher = Watcher(lgg, runner.in1, runner.out1, runner.in2, runner.out2)

    wm = WatchManager()
    notifier = Notifier(wm, watcher)
    watchdir = os.path.dirname(watcher.in1)
    lgg.info("Watching " + watchdir)
    wdd = wm.add_watch(watchdir, EventsCodes.ALL_FLAGS['IN_MODIFY'], rec=False)
    notifier.loop()


if __name__ == '__main__':
    main()