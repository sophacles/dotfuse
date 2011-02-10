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
    ''' dummy method to avoid conflating fs errors and jinja errors
    Updated to provide a listing according to the fs at runtime,
    potentially making this a nice little debugging tool
    '''
    res = "%s\n" % path
    for x in os.walk(path):
        res = "%s%s\n" % (res, x)
    return res

def log(string):
    return
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

        # TODO: Command line parameters to add:
        #   -b : fs base (absbase)
        #   -e : python file containing various environment params globally
        #   -t : target dir, place to write resultant files (and make default ~)
        #   -l : turn on logging (to file -lf)

        self.absbase = os.path.expanduser('~/.dotfs')
        if not os.path.exists(self.absbase):
            os.mkdir(self.absbase)
        elif not os.path.isdir(self.absbase):
            raise Exception("Problem with absbase")

        log( 'Init complete.')

    def getattr(self, path):
        """
        return the result of os.stat on the real fs object represented by path.
        """

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
            log('Error! got: %s' % e)
            raise


    def statfs(self, path):
        ''' return a statvfs object about the underlining base fs'''
        log('statfs called')
        #pythonl has statvfs... just saying
        s = os.statvfs(J(self.absbase, path[1:]))

        # someday fix up fuse to do this crap for us.. take a statvfs object and
        # return a fuse.StatVfs from it... souts simple enough, right?
        st = fuse.StatVfs()
        st.f_bsize = s.f_bsize
        st.f_frsize = s.f_frsize
        st.f_blocks = s.f_blocks
        st.f_bfree = s.f_bfree
        st.f_bavail = s.f_bavail
        st.f_files = s.f_files
        st.f_ffree = s.f_ffree
        st.f_favail = s.f_favail
        st.f_flag = s.f_flag
        st.f_namemax = s.f_namemax
        return  st

    def unlink(self, path):
        '''file deletion method, pasthru to os module equiv'''
        log('unlink called: %s' % (path, ))
        try:
            os.unlink(J(self.absbase,path[1:]))
        except Exception, e:
            log('unlink got: %s' % (e,))
            raise e
        return 0

    def mkdir(self, path, mode):
        '''make a directory. passthrough to os module equiv'''
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
        used in things like file listings and whatnot
        thin wrapper on os.listdir
        return: [[('file1', 0), ('file2', 0), ... ]]
        """

        #log('readdir: %s, %s' % (path, offset))
        path = path[1:]

        yield Direntry('.')
        yield Direntry('..')
        for x in os.listdir(J(self.absbase, path)):
            yield Direntry(x)

    def open(self, path, flags):
        ''' tries to open the file, then closes it right away.
        makes sure the file exists etc, but doesn't track anything.
        basically a "make the fs happy" method
        '''
        log('open called: %s %s' % (path, flags))
        try:
            # TODO: make o_append an invalid flag, as that crap
            # is a pain to track. alternately include it, but good luck :P
            mypath = J(self.absbase,path[1:])
            x = os.open(mypath, flags)
            os.close(x)
        except Exception, e:
            log('open %s got error: %s' % (mypath, e))
            raise e
        return 0

    def read(self, path, readlen, offset):
        ''' Open a file, read the appropriate chunks, close.  One of many
        reasons this fs shouldn't be used for serious work outside the
        dotfiles.  This would be really inefficient in high load scenarios'''

        log('read called: %s %s %s' % (path, readlen, offset))
        mypath = J(self.absbase, path[1:])

        fsize = os.stat(mypath).st_size
        log('read opening %s' % mypath)
        x = open(mypath, 'r')
        x.seek(offset)
        res x.read(readlen)
        x.close()
        return res

    def write(self, path, vals, offset):
        ''' Open the file with mode 'w' then write to it. Note, this means that
        every call to write is a full fledged truncat/write scenario. Some
        might consider this a bug, but for now it works as that is how vim
        seems to work for my testing purposes. Blocking and therefore writes
        the whole file. Also haven't tested with files biger than 4096. Hrm...
        more potential issues there :/
        '''

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
        '''pasthrough to os.truncate'''
        log('truncate called: %s %s' %  (path, size))
        fd = open(J(self.absbase, path[1:]), 'r+')
        fd.truncate(size)
        fd.close()

        return 0

    def fsync(self, path, isfsyncfile):
        ''' don't want to do anything here, but not implementing it is a pita'''
        log('fsync called: %s %s' % (path, isfsyncfile))
        return 0

    def flush(self, path):
        '''this is the meat and potatoes of this fs. see the docs for details on how
        it works, but in short it is awesome.'''

        # TODO: implement a way to get code loaded from _$first/$first.py?
        #   pros: not really any less secure at thise point
        #   cons: crash the fs? break other things?
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
        ''' just separating out the crap for jinja and the file traking.
        also may allow for some sort of strategy pattern on rendering in the
        future if this takes off or something'''
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
        '''implements the stuff for o_create so various things
        can be happy (like touch)'''

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


    ## Stubs for all the other potenially called functions. Maybe figure out
    ## A beter place for them, but they turn out to be useful enough to bugging that
    #@ not having them is a pain in the butt

    # TODO: implement a test harness type metaclass for this, wwhere the full list of
    # potential functions is iterated, and the ones without actual implementations get
    # the stubs like below

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

    ## Different type of debugging. Also add to experimental coding thing?

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

