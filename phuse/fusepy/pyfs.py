#!/usr/bin/env python
#
# Implementation of a filesystem that will show a file and a directory
# when executing ls on the root.
#
# Copyright (c) 2013 Murat Knecht
# License: MIT
#

import errno
from itertools import chain
import logging
import stat
import sys

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


class PyFS(fuse.Operations):

    def __init__(self):
        super(PyFS, self).__init__()
        for name in ("json", "os", "sys"):
            add_module(name)

    @logcall
    def getattr(self, path, fh=None):
        if path == '/' or path == "/." or path == "/..":
            return dict(
                st_mode=stat.S_IFDIR | 0555,
                st_nlink=2,
            )
        elif is_dir(path):
            return dict(
                st_mode=stat.S_IFDIR | 0555,
                st_nlink=3,
            )
        elif is_file(path):
            def _get_file_mode():
                if is_executable(path):
                    return 0555
                elif path == PATH_MODULES:
                    return 0666
                else:
                    return 0444
            return dict(
                st_mode=stat.S_IFREG | _get_file_mode(),
                st_nlink=1,
                st_size=len(get_content(path)),
            )
        else:
            raise fuse.FuseOSError(errno.ENOENT)

    @logcall
    def read(self, path, size, offset, fh):
        return read_from_string(
            get_content(path),
            size,
            offset,
        )

    @logcall
    def readdir(self, path, fh):
        return (name for name in chain([".", ".."], get_elements(path)))


if __name__ == '__main__':
    logging.basicConfig(filename="pyfs.log", filemode="w")
    logging.getLogger().setLevel(logging.DEBUG)
    fuse.FUSE(PyFS(), sys.argv[1])
