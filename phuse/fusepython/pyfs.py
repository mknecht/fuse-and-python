#!/usr/bin/env python
import errno
import logging
import os
import stat

import fuse

from phuse.common import (
    add_module,
    is_dir,
    is_executable,
    is_file,
    get_content,
    get_elements,
    logcall,
    PATH_MODULES,
    read_from_string,
    reset_modules_list,
)


fuse.fuse_python_api = (0, 2)
log = logging.getLogger(__name__)


class DirectoryMapping(object):
    @logcall
    def __init__(self, path):
        log.debug("opendir(path={})".format(path))
        self.path = path

    def readdir(self, offset):
        log.debug("readdir(offset={}, path={})".format(offset, self.path))
        for name in [".", ".."] + get_elements(self.path):
            yield fuse.Direntry(name)


class FileMapping(object):
    @logcall
    def __init__(self, path, flags, **kw):
        if path == PATH_MODULES:
            self.append = flags & os.O_APPEND
            if flags & os.O_RDWR:
                log.debug("Cannot allow readwrite access. Flags: {}".format(
                    flags
                ))
                raise IOError(-errno.EPERM)
            if flags & os.O_TRUNC:
                reset_modules_list()
        else:
            if flags & os.O_WRONLY or flags & os.O_RDWR:
                log.debug("Cannot write to Python objects. Flags: {}".format(
                    flags
                ))
                raise IOError(-errno.EPERM)
        self.path = path
        # Workaround for uncleared exception state.
        # Real bugfix:
        # http://sourceforge.net/p/fuse/fuse-python/ci/7e29c2aeedf908732121559a31ba615b4c058fab/  # noqa
        # Comment out, if you see this in strace, meaning you don't have a
        # patched version yet:
        # open("mountpoint/run/modules", O_WRONLY|O_CREAT|O_TRUNC, 0666) = -1 EINVAL (Invalid argument)  # noqa
        #
        # self.direct_io = False
        # self.keep_cache = False

    @logcall
    def get_text(self):
        return get_content(self.path)

    @logcall
    def read(self, size, offset, *args):
        return read_from_string(
            self.get_text(),
            size,
            offset,
        )

    @logcall
    def write(self, buf, offset):
        if not self.append and offset != 0:
            log.debug("Must either append to or truncate a file.")
            raise IOError(-errno.EPERM)
        if buf.strip():
            add_module(buf.strip())
        return len(buf)


class PyFS(fuse.Fuse):
    dir_class = DirectoryMapping
    file_class = FileMapping

    def __init__(self):
        super(PyFS, self).__init__(dash_s_do='setsingle')
        for name in ("json", "os", "sys"):
            add_module(name)

    @logcall
    def getattr(self, path):
        log.debug("getattr(path={})".format(path))
        st = fuse.Stat()
        if path == '/' or path.endswith("/.") or path.endswith("/.."):
            st.st_mode = stat.S_IFDIR | 0555
            st.st_nlink = 2
        elif is_dir(path):
            st.st_mode = stat.S_IFDIR | 0555
            st.st_nlink = 3
        elif is_file(path):
            st.st_mode = stat.S_IFREG
            if is_executable(path):
                st.st_mode |= 0555
            elif path == PATH_MODULES:
                st.st_mode |= 0666
            else:
                st.st_mode |= 0444
            st.st_nlink = 1
            st.st_size = len(FileMapping(path, os.O_RDONLY).get_text())
        else:
            return -errno.ENOENT
        return st

    @logcall
    def truncate(self, path, len, *args):
        if path != PATH_MODULES:
            raise IOError(-errno.EPERM)
        if len != 0:
            raise IOError(-errno.EPERM)
        reset_modules_list()


def main():
    logging.basicConfig(filename="pyfs.log", filemode="w")
    logging.getLogger().setLevel(logging.DEBUG)
    server = PyFS()
    server.parse()
    log.debug("Starting filesystem")
    server.main()

if __name__ == '__main__':
    main()
