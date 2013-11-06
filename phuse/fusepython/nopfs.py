#!/usr/bin/env python
#
# Copyright (c) 2013 Murat Knecht
# License: MIT
#

import fuse

fuse.fuse_python_api = (0, 2)


class NopFS(fuse.Fuse):
    pass


def main():
    server = NopFS()
    server.parse()
    server.main()

if __name__ == '__main__':
    main()
