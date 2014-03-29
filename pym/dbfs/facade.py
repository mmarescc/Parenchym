import os
import re
import fs
import fs.base


class PymFs(fs.base.FS):

    _re_invalid_chars = re.compile(r'[\x00-\x1f\x7f]+')
    """
    Invalid characters for a filename in filesystem.

    - NULL byte
    - Control characters 0x01..0x1f (01..31)
    - Escape Character 0x7f (127)
    """


class PymPgFs(PymFs):

    _meta = {
        'read_only': False,
        'thread_safe': True,
        'network': False,
        'unicode_paths': True,
        'case_insensitive_paths': False,
        'atomic.makedir': True,
        'atomic.rename': True,
        'atomic.setcontents': True,
        'virtual': False
    }

    def __init__(self, root_path, thread_synchronize=True):
        """
        Creates an FS object that represents the PgFs under a given root path.

        :param root_path: Root path in resource tree. Must exist.
        :param thread_synchronize: If True, this object will be thread-safe by
            use of a threading.Lock object
        """

        super().__init__(thread_synchronize=thread_synchronize)
        root_path = os.path.normpath(root_path)

        if not self.exists(root_path):
            raise fs.errors.ResourceNotFoundError(root_path,
                msg="Root directory does not exist: %(path)s")
        self.root_path = root_path

    def __repr__(self):
        return "<{cls}: {r}>".format(cls=self.__class__.__name__,
            r=self.root_path)

    def exists(self, path):
        # TODO Implement
        return True

    def makedir(self, path, recursive=False, allow_recreate=False):
        # TODO Implement
        pass

    def getmeta(self, meta_name, default=fs.base.NoDefaultMeta):
        if meta_name == 'free_space':
            return 0  # TODO Implement
        elif meta_name == 'total_space':
            return 0  # TODO Implement
        return super().getmeta(meta_name, default)
