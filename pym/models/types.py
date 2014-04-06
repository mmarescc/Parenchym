import sqlalchemy as sa
import sqlalchemy.types

import pym.lib


class CleanUnicode(sa.types.TypeDecorator):
    """
    Type for a cleaned unicode string.

    Usage::

        CleanUnicode(255)

    """

    impl = sa.Unicode

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        value = pym.lib.clean_string(value)
        return value
