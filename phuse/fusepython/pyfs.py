#!/usr/bin/env python
import errno
import importlib
import logging
import os
import stat
import traceback
import types

import fuse

from phuse.common import logcall


fuse.fuse_python_api = (0, 2)
log = logging.getLogger(__name__)

VALUE_TYPES = [
    types.BooleanType,
    types.ComplexType,
    types.DictProxyType,
    types.DictType,
    types.DictionaryType,
    types.FileType,
    types.FloatType,
    types.IntType,
    types.ListType,
    types.LongType,
    types.NoneType,
    types.StringType,
    types.StringTypes,
    types.TracebackType,
    types.TupleType,
]

PATH_MODULES = "/run/modules"

root_namespace = {
    "run": {"modules": None},
    "lib": {},
}


def addlib(name):
    try:
        root_namespace["lib"][name] = importlib.import_module(name)
    except ImportError:
        log.debug(traceback.format_exc())
        raise IOError(-errno.ENXIO)


def path_to_qname(path):
    return [n for n in path.split("/") if n]


def resolve(qname):
    log.debug("Resolving: {}".format(qname))
    obj = None
    parts = qname[:]
    while parts:
        name = parts.pop(0)
        if obj is None:
            obj = root_namespace[name]
        elif len(qname) - len(parts) == 2:
            obj = obj[name]
        else:
            pyname = name[1:] if name.startswith(".") else name
            obj = getattr(obj, pyname)
    log.debug("Resolved {} to {})".format(qname, obj))
    return obj


def is_dir(path):
    return (
        path[1:] in root_namespace or
        isinstance(resolve(path_to_qname(path)), types.ModuleType)
    )


def is_file(path):
    return (
        is_executable(path) or
        is_datafile(path)
    )


def is_executable(path):
    return (
        hasattr(resolve(path_to_qname(path)), "__call__")
    )


def is_datafile(path):
    return (
        path == PATH_MODULES or
        any(
            isinstance(resolve(path_to_qname(path)), type_)
            for type_ in VALUE_TYPES
        )
    )


@logcall
def get_elements(path):
    log.debug("Getting contents for: {}".format(path))
    qname = path_to_qname(path)

    def _get_visible_elements():
        if qname == []:
            return root_namespace.keys()
        if len(qname) == 1:
            return root_namespace[path[1:]].keys()
        else:
            return dir(resolve(qname))

    all_names = []
    for name in _get_visible_elements():
        all_names.append(
            "{prefix}{name}".format(
                prefix="." if name.startswith("_") else "",
                name=name,
            )
        )
    log.debug("Got unfiltered elements for path {}: {}".format(
        path, all_names))

    chosen_names = []
    for name in all_names:
        if len(qname) == 0:
            chosen_names.append(name)
        else:
            child_path = "/" + "/".join(qname + [name])
            if is_file(child_path) or is_dir(child_path):
                chosen_names.append(name)
    log.debug("For {} got contents: {}".format(path, chosen_names))
    return chosen_names


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
    __EXEC_TEMPLATE = """#!/usr/bin/python

import sys
import {modulename}

if __name__ == '__main__':
    print({modulename}.{functionname}(*sys.argv[1:]))

"""

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
                root_namespace["lib"] = {}
        else:
            if flags & os.O_WRONLY or flags & os.O_RDWR:
                log.debug("Cannot write to Python objects. Flags: {}".format(
                    flags
                ))
                raise IOError(-errno.EPERM)
        self.path = path
        # Workaround for uncleared exception state. Real bugfix:
        # http://sourceforge.net/p/fuse/fuse-python/ci/7e29c2aeedf908732121559a31ba615b4c058fab/  # noqa
        # self.direct_io = False
        # self.keep_cache = False

    @logcall
    def read(self, size, offset, *args):
        log.debug("read(size={}, offset={}, args={}, path={})".format(
            size, offset, args, self.path))
        return self._read_from_string(
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
            addlib(buf.strip())
        return len(buf)

    @logcall
    def get_text(self):
        if self.path == PATH_MODULES:
            return "\n".join(root_namespace["lib"].keys())
        else:
            return self._render_template()

    def _read_from_string(self, text, size, offset):
        slen = len(text)
        if offset < slen:
            if offset + size > slen:
                size = slen - offset
            buf = text[offset:offset+size]
        else:
            buf = ''
        return buf

    @logcall
    def _render_template(self):
        qname = path_to_qname(self.path)
        if is_executable(self.path):
            return self.__EXEC_TEMPLATE.format(
                modulename=".".join(qname[1:-1]),
                functionname=qname[-1],
            )
        elif is_datafile(self.path):
            obj = resolve(qname)
            if isinstance(obj, list):
                return os.linesep.join(obj)
            return str(obj)
        else:
            raise IOError("Cannot read unknown filetype", errno.ENOTSUP)


class PyFS(fuse.Fuse):
    dir_class = DirectoryMapping
    file_class = FileMapping

    def __init__(self):
        super(PyFS, self).__init__(dash_s_do='setsingle')
        for name in ("json", "os", "sys"):
            addlib(name)

    @logcall
    def truncate(self, path, len, *args):
        if path != PATH_MODULES:
            raise IOError(-errno.EPERM)
        if len != 0:
            raise IOError(-errno.EPERM)
        root_namespace["lib"] = {}

    @logcall
    def getattr(self, path):
        log.debug("getattr(path={})".format(path))
        st = fuse.Stat()
        if path == '/' or path.endswith("/.") or path.endswith("/.."):
            st.st_mode = stat.S_IFDIR | 0555
            st.st_nlink = 2
        elif is_dir(path):  # Needs to come before
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


def main():
    logging.basicConfig(filename="pyfs.log", filemode="w")
    logging.getLogger().setLevel(logging.DEBUG)
    server = PyFS()
    server.parse()
    log.debug("Starting filesystem")
    server.main()

if __name__ == '__main__':
    main()
