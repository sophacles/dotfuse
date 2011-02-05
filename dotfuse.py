#!/usr/bin/python

from fuse import Fuse, Stat, Direntry

from time import time

import stat    # for file properties
import os      # for filesystem modes (O_RDONLY, etc)
import errno   # for error number codes (ENOENT, etc)
               # - note: these must be returned as negatives

from os.path import join as J

def run_template(path):
    res = "%s\n" % path
    for x in os.walk(path):
        res = "%s%s\n" % (res, x)
    return res

class DotFS(Fuse):
    """
    """

    def __init__(self, *args, **kw):
        Fuse.__init__(self, *args, **kw)

        self.abspath
        self.files = dict()
        print 'Init complete.'

    def getattr(self, path):
        """
        - st_mode (protection bits)
        - st_ino (inode number)
        - st_dev (device)
        - st_nlink (number of hard links)
        - st_uid (user ID of owner)
        - st_gid (group ID of owner)
        - st_size (size of file, in bytes)
        - st_atime (time of most recent access)
        - st_mtime (time of most recent content modification)
        - st_ctime (platform dependent; time of most recent metadata change on Unix,
                    or the time of creation on Windows).
        """

        # NOTE: what is this path? absolute, or relative to this fs?
        try:
            s = os.stat(J(self.absbase, path))
            return Stat(
                st_mode=s.st_mode,
                st_ino=s.st_ino,
                st_dev=s.st_dev,
                st_nlink=s.st_nlink,
                st_uid=s.st_uid,
                st_gid=s.st_gid,
                st_size=s.st_size,
                st_atime=s.st_atime,
                st_mtime=s.st_mtime,
                st_ctime=s.st_ctime
                )

        except OSError, e:
            return -e.errno


    def readlink(self, path ):
        print '*** readlink', path
        return -errno.ENOSYS

    def readdir(self, path):
        """
        return: [[('file1', 0), ('file2', 0), ... ]]
        """

        yield Direntry('.')
        yield Direntry('..')
        for x in os.listdir(J(self.absbase, path)):
            yield Direntry(x)

    def open(self, path, flags):
        x = open(J(abspath,path), flags)
        x.close()

    def read(self, path, readlen, offset):
        fsize = os.stat(J(self.abspath, path)).st_size
        x = open(J(self.abspath, path), 'r')
        x.seek(offset)
        d = x.read(readlen)
        if offset < fsize:
            return x.read(readlen)
        else:
            return ''

    def write(self, path, vals, offset):
        x = open(J(self.abspath, path), 'r')
        x.seek(offset)
        written = x.write(vals)
        x.close()
        return written

    def fsync(self, path, isfsyncfile):
        if not path.startswith('_'):
            return 0
        first, rest = path.partition('/')[::2]
        if not os.path.exists(J(self.abspath, first, first[1:])):
            return 0
        try:
            x = run_template(J(self.abspath, first, first[1:]))
        except Exception, e:
            log('Exception running template for %s: %s' %
                    (J(self.abspath, first, first[1:]), e))

            return 0
        fd = open(J(os.path.expanduser('~'), 'dotfstest', '.' + first[1:]))
        fd.write(x)
        fd.close()
        return 0

if __name__ == __main__:
    fs = NullFS()
    fs.flags = 0
    fs.multithreaded = 0
    fs.main()

