#!/usr/bin/env python
#
# Minimalist implementation of a filesystem with fusepy
# that is still mountable.
#
# Copyright (c) 2013 Murat Knecht
# License: MIT
#
import sys

import fuse


class NopFS(fuse.Operations):
    pass

if __name__ == '__main__':
    fuse.FUSE(NopFS(), sys.argv[1])
