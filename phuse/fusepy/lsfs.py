#!/usr/bin/env python
#
# Implementation of a filesystem that will show a file and a directory
# when executing ls on the root.
#
# Copyright (c) 2013 Murat Knecht
# License: MIT
#

import errno
import stat
import sys

import fuse


class LsFS(fuse.Operations):
    def getattr(self, path, fh=None):
        if path[1:] == "some_dir" or path == '/':
            return dict(
                st_mode=(stat.S_IFDIR | 0755),
                st_nlink=2,
            )
        elif path[1:] == "some_file":
            return dict(
                st_mode=(stat.S_IFREG | 0644),
                st_nlink=1,
            )
        else:
            raise fuse.FuseOSError(errno.ENOENT)

    def readdir(self, path, fh):
        if path == "/":
            return [".", "..", "some_file", "some_dir"]


if __name__ == '__main__':
    fuse.FUSE(LsFS(), sys.argv[1])
