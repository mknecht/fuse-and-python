import sys

import fuse


class NopFS(fuse.Operations):
    pass

if __name__ == '__main__':
    fuse.FUSE(NopFS(), sys.argv[1])
