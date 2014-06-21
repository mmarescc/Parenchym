# -*- coding: utf-8 -*-


_ = lambda s: s


class PymError(Exception):
    pass


class AuthError(PymError):
    pass


class SassError(PymError):

    def __init__(self, msg, resp=None):
        super().__init__(msg)
        self.resp = resp


class SchedulerError(PymError):
    pass
