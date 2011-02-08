#!/usr/bin/python

import fuse
from fuse import Fuse, Stat, Direntry

from time import time

import stat    # for file properties
import os      # for filesystem modes (O_RDONLY, etc)
import errno   # for error number codes (ENOENT, etc)
               # - note: these must be returned as negatives

from os.path import join as J
import jinja2

fuse.fuse_python_api = (0, 2)

def run_template(path):
    res = "%s\n" % path
    for x in os.walk(path):
        res = "%s%s\n" % (res, x)
    return res

def log(string):
    try:
        fd = open('./logfile', 'a')
        fd.write("ENTRY: %s\n" % string)
        fd.close()
    except Exception, e:
        print '*****************ERROR*****************'
        print 'while logging:'
        print s
        print 'got: ', e




class DotFS(Fuse):
    """
    """

    def __init__(self, *args, **kw):
        Fuse.__init__(self, *args, **kw)

        self.absbase = os.path.expanduser('~/.dotfs')
        if not os.path.exists(self.absbase):
            os.mkdir(self.absbase)
        elif not os.path.isdir(self.absbase):
            raise Exception("Problem with absbase")

        # TODO: Put a context in here with whatever.

        log( 'Init complete.')

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
        log('getattr called on: %s' % (path,))
        if path.startswith('/'): path = path[1:]

        try:
            mypath =J(self.absbase, path)
            #log('calling stat on: %s' % mypath)
            s = os.stat(mypath)
            res =  Stat(
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
            log('returning: %s' %s)
            return res
        except OSError, e:
            #log('Error! got: %s' % e)
            raise


    def statfs(self, *args, **kw):
        log('statfs called')
        #pythonl has statvfs... just saying
        st = fuse.StatVfs()
        st.f_frsize = 0 #block_size
        st.f_blocks = 0 #blocks
        st.f_bfree = 0 #blocks_free
        st.f_bavail = 0 #blocks_avail
        st.f_files = 0 #files
        st.f_ffree = 0 #files_free
        st.f_flag = 0 #
        st.f_namemax = 255
        return  st

    def unlink(self, path):
        log('unlink called: %s' % (path, ))
        try:
            os.unlink(J(self.absbase,path[1:]))
        except Exception, e:
            log('unlink got: %s' % (e,))
            raise e
        return 0

    def mkdir(self, path, mode):
        log('mkdir called: %s %o' % (path, mode))
        mypath = J(self.absbase, path[1:])
        try:
            os.mkdir(mypath, mode)
        except Exception, e:
            log('mkdir got error making %s: %s' % (mypath, e))
            raise e

        return 0

    def readdir(self, path, offset):
        """
        return: [[('file1', 0), ('file2', 0), ... ]]
        """

        #log('readdir: %s, %s' % (path, offset))
        path = path[1:]

        yield Direntry('.')
        yield Direntry('..')
        for x in os.listdir(J(self.absbase, path)):
            yield Direntry(x)

    def open(self, path, flags):
        log('open called: %s %s' % (path, flags))
        try:
            mypath = J(self.absbase,path[1:])
            x = os.open(mypath, flags)
            os.close(x)
        except Exception, e:
            log('open %s got error: %s' % (mypath, e))
            raise e
        return 0

    def read(self, path, readlen, offset):
        log('read called: %s %s %s' % (path, readlen, offset))
        mypath = J(self.absbase, path[1:])

        fsize = os.stat(mypath).st_size
        log('read opening %s' % mypath)
        x = open(mypath, 'r')
        x.seek(offset)
        return x.read(readlen)

    def write(self, path, vals, offset):
        log('write called: %s %s %s' % (path, vals, offset))
        mypath = J(self.absbase, path[1:])
        x = open(mypath, 'w')
        log('write! b')
        #x.seek(offset)
        written = x.write(vals)
        x.close()
        log('wrote: %s' % len(vals))
        return len(vals)

    def truncate(self, path, size):
        log('truncate called: %s %s' %  (path, size))
        fd = open(J(self.absbase, path[1:]), 'r+')
        fd.truncate(size)
        fd.close()

        return 0

    def fsync(self, path, isfsyncfile):
        log('fsync called: %s %s' % (path, isfsyncfile))
        return 0

    def flush(self, path):
        log('flush called: %s' % (path, ))

        path = path[1:]
        if not path.startswith('_'):
            log('not a tmplate path')
            return 0
        first, rest = path.partition('/')[::2]
        if not os.path.exists(J(self.absbase, first, first[1:])):
            log('no template base')
            return 0
        try:
            log('templating!')
            # First line testing, second, eventual production
            # x = run_template(J(self.absbase, first))
            x = self.render_config(first)
        except Exception, e:
            log('Exception running template for %s:(%s) %s' %
                    (J(self.absbase, first, first[1:]),type(e), e))

            return -errno.EIO

        log('witing file')
        try:
            fd = open(J(os.path.expanduser('~'), 'dotfstest', '.' + first[1:]), 'w')
            fd.write(x)
            fd.close()
            return 0

        except Exception, e:
            log('got error: %s' %e)
            raise e

    def render_config(self, ctxpath):
        log('render_config: %s' % ctxpath)
        fullctx = J(self.absbase,ctxpath)
        fname = ctxpath[1:]
        log('render_config: fullctx = %s; fname = %s' % (fullctx, fname))
        tenv = jinja2.Environment(loader=jinja2.FileSystemLoader(fullctx))
        log('render_config: loading')
        t = tenv.get_template(fname)
        log('render_config: actually rendering!')
        res = t.render()
        log('render_config: got:\n %s' % res)
        return res

    def create(self, path, flags, mode):
        log('create called: %s %s %s' % (path, flags, mode))
        mypath = J(self.absbase,path[1:])
        try:
            x = os.open(mypath, flags, stat.S_IMODE(mode))
            os.close(x)
            #fd = open(mypath, 'w', stat.S_IMODE(mode))
            #fd.close()
        except Exception, e:
            log('(in create) opening %s got: %s' % (mypath, e))
        return 0


    ## GUESES

    #def chmod(self, *args, **kw):
    #    log('chmod called: %s %s' % (args, kw))
    #    return -2

    #def access(self, *args, **kw):
    #    log('access called: %s %s' % (args, kw))
    #    return -2

    #def bmap(self, *args, **kw):
    #    log('bmap called: %s %s' % (args, kw))
    #    return 0
    #def utimens(self, *args, **kw):
    #    log('utimens called: %s %s' % (args, kw))
    #    return 0
    #def utime(self, *args, **kw):
    #    log('utime called: %s %s' % (args, kw))
    #    return 0

    #def chown(self, *args, **kw):
    #    log('chown called: %s %s' % (args, kw))
    #    return 0

    #def fgetattr(self, *args, **kw):
    #    log('fgetattr called: %s %s' % (args, kw))
    #    return 0

    #def ftruncate(self, *args, **kw):
    #    log('ftruncate called: %s %s' %  (args, kw))
    #    return 0
    #def lock(self, *args, **kw):
    #    log('lock called: %s %s' % (args, kw))
    #    return 0
    #def release(self, *args, **kw):
    #    log('release called: %s %s' % (args, kw))
    #    return 0
    #def mknod(self, *args, **kw):
    #    log('mknod called: %s %s' % (args, kw))
    #    return 0
    #def fsyncdir(self, *args, **kw):
    #    log('fsyncdir called: %s %s' % (args, kw))
    #    return 0
    #def link(self, *args, **kw):
    #    log('link called: %s %s' % (args, kw))
    #    return 0
    #def readlink(self, *args, **kw):
    #    log('readlink called: %s %s' % (args, kw))
    #    return 0
    #def rename(self, *args, **kw):
    #    log('rename called: %s %s' % (args, kw))
    #    return 0
    #def symlink(self, *args, **kw):
    #    log('symlink called: %s %s' % (args, kw))
    #    return 0
    #def rmdir(self, *args, **kw):
    #    log('rmdir called: %s %s' % (args, kw))
    #    return 0
    #def opendir(self, *args, **kw):
    #    log('opendir called: %s %s' % (args, kw))
    #    return 0
    #def releasedir(self, *args, **kw):
    #    log('releasedir called: %s %s' % (args, kw))
    #    return 0
    #def fsinit(self, *args, **kw):
    #    log('fsinit called: %s %s' % (args, kw))
    #    return 0
    #def fsdestroy(self, *args, **kw):
    #    log('fsdestroy called: %s %s' % (args, kw))
    #    return 0
    #def setxattr(self, *args, **kw):
    #    log('setxattr called: %s %s' % (args, kw))
    #    return 0
    #def getxattr(self, *args, **kw):
    #    log('getxattr called: %s %s' % (args, kw))
    #    return 0
    #def removexattr(self, *args, **kw):
    #    log('removexattr called: %s %s' % (args, kw))
    #    return 0
    #def listxattr(self, *args, **kw):
    #    log('listxattr called: %s %s' % (args, kw))
    #    return 0

    # def __getattribute__(self, attr):
    #     s = "looking for %s\n " % attr
    #     try:
    #         res = Fuse.__getattribute__(self, attr)
    #     except Exception, e:
    #         s += "\tgot excepton: %s" % e
    #         log(s)
    #         raise e
    #     s += "\tgot: %s" % res
    #     log(s)
    #     return res

if __name__ == '__main__':
    fs = DotFS()
    fs.flags = 0
    fs.multithreaded = 0
    fs.parse()
    fs.main()

