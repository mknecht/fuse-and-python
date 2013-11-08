#!/usr/bin/env python
import errno
import json
import logging
import os
import stat
import types

import fuse

fuse.fuse_python_api = (0, 2)
log = logging.getLogger(__name__)


global_namespace = {}


def path_to_qname(path):
    return [n for n in path.split("/") if n]


def resolve(qname):
    log.debug("Resolving: {}".format(qname))
    obj = None
    parts = qname[:]
    while parts:
        name = parts.pop(0)
        obj = global_namespace[name] if obj is None else getattr(obj, name)
    log.debug("Resolved {} to {})".format(qname, obj))
    return obj


def is_dir(path):
    return isinstance(resolve(path_to_qname(path)), types.ModuleType)


def is_file(path):
    return isinstance(resolve(path_to_qname(path)), types.FunctionType)


def get_elements(path):
    log.debug("Getting contents for: {}".format(path))
    qname = path_to_qname(path)
    all_names = [
        entry
        for entry in dir(resolve(qname))
    ]
    log.debug("Got unfiltered elements for path {}: {}".format(
        path, all_names))
    chosen_names = []
    for name in all_names:
        element = resolve(qname + [name])
        if (
                isinstance(element, types.FunctionType) or
                isinstance(element, types.ModuleType)
        ):
            chosen_names.append(name)
    log.debug("For {} got contents: {}".format(path, chosen_names))
    return chosen_names


class DirectoryMapping(object):
    def __init__(self, path):
        log.debug("opendir(path={})".format(path))
        self.path = path

    def readdir(self, offset):
        log.debug("readdir(offset={}, path={})".format(offset, self.path))
        if self.path == "/":
            for name in [".", ".."] + global_namespace.keys():
                yield fuse.Direntry(name)
        else:
            for name in [".", ".."] + get_elements(self.path):
                yield fuse.Direntry(name)


class FileMapping(object):
    __TEMPLATE = """#!/usr/bin/python

import sys
import {modulename}

if __name__ == '__main__':
    print({modulename}.{functionname}(*sys.argv[1:]))

"""

    def __init__(self, path, *args):
        log.debug("FileMapping(path={}, args={})".format(path, args))
        self.path = path

    def read(self, size, offset, *args):
        log.debug("read(size={}, offset={}, args={}, path={})".format(
            size, offset, args, self.path))
        rendered = self.render_template()
        slen = len(rendered)
        if offset < slen:
            if offset + size > slen:
                size = slen - offset
            buf = rendered[offset:offset+size]
        else:
            buf = ''
        return buf

    def render_template(self):
        qname = path_to_qname(self.path)
        return self.__TEMPLATE.format(
            modulename=".".join(qname[:-1]),
            functionname=qname[-1],
        )


class PyFS(fuse.Fuse):
    dir_class = DirectoryMapping
    file_class = FileMapping

    def __init__(self):
        super(PyFS, self).__init__(dash_s_do='setsingle')
        global_namespace["json"] = json
        global_namespace["os"] = os

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
            st.st_mode = stat.S_IFREG | 0555
            st.st_nlink = 1
            st.st_size = len(FileMapping(path).render_template())
        else:
            return -errno.ENOENT
        return st


def main():
    logging.basicConfig(filename="pyfs.log", filemode="w")
    logging.getLogger().setLevel(logging.DEBUG)
    server = PyFS()
    server.parse()
    log.debug("Starting filesystem")
    server.main()

if __name__ == '__main__':
    main()
