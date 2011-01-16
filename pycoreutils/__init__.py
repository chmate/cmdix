#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2009, 2010, 2011 Hans van Leeuwen.
# See LICENSE.txt for details.

from __future__ import print_function, unicode_literals
from wsgiref import simple_server
import base64
import bz2
import cmd
import gzip
import hashlib
import optparse
import os
import platform
import pprint
import shutil
import signal
import ssl
import stat
import sys


if sys.version_info[0] == 2:
    if sys.version_info[1] < 6:
        raise Exception("Pycoreutils requires Python version 2.6 or greater")


__version__ = '0.0.6a'
__license__ = '''Copyright (c) 2009, 2010, 2011 Hans van Leeuwen

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
'''

_cmds = []  # Commands will be added to this list


### DECORATORS ##############################################################


def addcommand(f):
    '''
    Register a command with pycoreutils
    '''
    _cmds.append(f)
    return f


def onlyunix(f):
    '''
    Decorator that indicates that the command cannot be run on windows
    '''
    f._onlyunix = True
    return f


### CLASSES #################################################################


class PyCoreutils(cmd.Cmd):

    exitstatus = 0
    prompttemplate = '{username}@{hostname}:{currentpath}$ '

    def __init__(self, *args, **kwargs):
        # Copy all commands from _cmds to a 'do_foo' function
        for func in _cmds:
            x = 'self.do_{0} = func'.format(func.__name__)
            exec(x)
        return cmd.Cmd.__init__(self, *args, **kwargs)

    def default(self, line):
        '''
        Called on an input line when the command prefix is not recognized.
        '''
        self.exitstatus = 127
        print("{0}: Command not found".format(line.split(None, 1)[0]))

    def do_exit(self, n=None):
        '''
        Exit the shell.

        Exits the shell with a status of N.  If N is omitted, the exit status
        is that of the last command executed.
        '''
        sys.exit(n or self.exitstatus)

    def do_help(self, arg):
        yield "Use 'COMMAND --help' for help\n"
        yield "Available commands:\n"
        yield ", ".join(listcommands()) + "\n"

    def do_shell(self, line):
        '''
        Run when them command is '!' or 'shell'.
        Execute the line using the Python interpreter.
        i.e. "!dir()"
        '''
        try:
            exec("pprint.pprint({0})".format(line))
        except Exception as err:
            pprint.pprint(err)

    def emptyline(self):
        '''
        Called when an empty line is entered in response to the prompt.
        '''
        print()

    def postcmd(self, stop, line):
        self.updateprompt()
        if stop:
            for l in stop:
                print(l, end='')

    def preloop(self):
        self.updateprompt()

    def runcommandline(self, commandline):
        s = ''
        for output in self.onecmd(commandline):
            s += output
        return s

    def updateprompt(self):
        '''
        Update the prompt using format() on the template in self.prompttemplate

        You can use the following keywords:
        - currentpath
        - hostname
        - username
        '''
        self.prompt = self.prompttemplate.format(
                                currentpath=os.getcwd(),
                                hostname=platform.node(),
                                username=getcurrentusername())


class WSGIServer(simple_server.WSGIServer):
    '''
    WSGIServer with SSL support
    '''
    def __init__(self, server_address, certfile=None, keyfile=None, \
                       ca_certs=None, ssl_version=ssl.PROTOCOL_SSLv23, \
                       handler=simple_server.WSGIRequestHandler):
        simple_server.WSGIServer.__init__(self, server_address, handler)
        self.allow_reuse_address = True
        self.certfile = certfile
        self.keyfile = keyfile
        self.ssl_version = ssl_version
        self.ca_certs = ca_certs

    def get_request(self):
        sock, addr = self.socket.accept()
        if self.certfile:
            sock = ssl.wrap_socket(sock,
                                    server_side=True,
                                    certfile=self.certfile,
                                    keyfile=self.keyfile,
                                    ssl_version=self.ssl_version,
                                    ca_certs=self.ca_certs)
        return sock, addr


class WSGIAuth():
    '''
    WSGI middleware for basic authentication
    '''
    def __init__(self, app, userdict, realm='authentication'):
        self.app = app
        self.userdict = userdict
        self.realm = realm

    def __call__(self, environ, start_response):
        if environ.has_key('HTTP_AUTHORIZATION'):
            authtype, authinfo = environ['HTTP_AUTHORIZATION'].split(None, 1)
            if authtype.upper() != 'BASIC':
                start_response(b'200 ', [(b'Content-Type', b'text/html')])
                return [b"Only basic authentication is supported"]
            encodedinfo = bytes(authinfo.encode())
            decodedinfo = base64.b64decode(encodedinfo).decode()
            username, password = decodedinfo.split(':', 1)
            if self.userdict.has_key(username):
                if self.userdict[username] == password:
                    return self.app(environ, start_response)

        return wsgierror(start_response, 401, "Authentication required",
                  [(b'WWW-Authenticate', b'Basic realm={0}'.format(self.realm))])


### HELPER FUNCTIONS ########################################################


def compressor(argstr, comptype='gzip', decompress=False):
    '''
    Handles compression and decompression as bzip2 and gzip
    '''
    p = parseoptions()
    p.description = "Compress or uncompress FILEs (by default, compress " + \
                    "FILES in-place)."
    p.usage = '%prog [OPTION]... [FILE]...'
    p.add_option("-c", "--stdout", "--as-stdout", action="store_true",
            dest="stdout",
            help="write on standard output, keep original files unchanged")
    p.add_option("-C", "--compresslevel", dest="compresslevel", type="int",
            default=6, help="set file mode (as in chmod), not a=rwx - umask")
    p.add_option("-d", "--decompress", action="store_true", dest="decompress",
            help="decompress")
    p.add_option("-1", "--fast", action="store_const", dest="compresslevel",
            const=1, help="Use the fastest type of compression")
    p.add_option("-2", action="store_const", dest="compresslevel", const=2,
            help="Use compression level 2")
    p.add_option("-3", action="store_const", dest="compresslevel", const=3,
            help="Use compression level 3")
    p.add_option("-4", action="store_const", dest="compresslevel", const=4,
            help="Use compression level 4")
    p.add_option("-5", action="store_const", dest="compresslevel", const=5,
            help="Use compression level 5")
    p.add_option("-6", action="store_const", dest="compresslevel", const=6,
            help="Use compression level 6")
    p.add_option("-7", action="store_const", dest="compresslevel", const=7,
            help="Use compression level 7")
    p.add_option("-8", action="store_const", dest="compresslevel", const=8,
            help="Use compression level 8")
    p.add_option("-9", "--best", action="store_const", dest="compresslevel",
            const=9, help="Use the best type of compression")
    (opts, args) = p.parse_args(argstr.split())
    prog = p.get_prog_name()

    if opts.help:
        return p.format_help()

    if comptype == 'gzip':
        compresstype = gzip.GzipFile
        suffix = '.gz'
    elif comptype == 'bzip' or comptype == 'bzip2':
        compresstype = bz2.BZ2File
        suffix = '.bz2'

    infiles = args

    # Use stdin for input if no file is specified or file is '-'
    if len(args) == 0 or (len(args) == 1 and args[0] == '-'):
        infiles = [sys.stdin]

    for infile in infiles:
        if opts.decompress or decompress:
            # Decompress
            infile = compresstype(infile, 'rb',
                                  compresslevel=opts.compresslevel)
            if len(args) == 0 or opts.stdout:
                outfile = sys.stdout
            else:
                unzippath = infile.rstrip(suffix)
                if os.path.exists(unzippath):
                    q = input("{0}: {1} already ".format(prog, unzippath) + \
                              "exists; do you wish to overwrite (y or n)? ")
                    if q.upper() != 'Y':
                        StdOutException("not overwritten", 2)

                outfile = open(unzippath, 'wb')
        else:
            # Compress
            zippath = infile + suffix
            infile = open(infile, 'rb')
            if len(args) == 0 or opts.stdout:
                outfile = sys.stdout
            else:
                if os.path.exists(zippath):
                    q = input("{0}: {1} already".format(prog, zippath) + \
                              " exists; do you wish to overwrite (y or n)? ")
                    if q.upper() != 'Y':
                        StdErrException("not overwritten", 2)

                outfile = compresstype(zippath, 'wb',
                                       compresslevel=opts.compresslevel)

        shutil.copyfileobj(infile, outfile)


def createcommandlinks(pycorepath, directory):
    '''
    Create a symlink to pycoreutils for every available command

    :param pycorepath:  Path to link to
    :param directory:   Directory where to store the links
    '''
    l = []
    for command in listcommands():
        linkname = os.path.join(directory, command)
        if os.path.exists(linkname):
            raise StdErrException("{0} already exists. Not doing anything.")
        l.append(linkname)

    for linkname in l:
        os.symlink(os.path.abspath(pycorepath), linkname)


def getcommand(commandname):
    '''
    Returns the function of the given commandname.
    Raises a CommandNotFoundException if the command is not found
    '''
    a = [cmd for cmd in _cmds if cmd.__name__ == commandname]
    l = len(a)
    if l == 0:
        raise CommandNotFoundException(commandname)
    if l > 1:
        raise "Command `{0}' has multiple functions ".format(commandname) +\
              "associated with it! This should never happen!"
    return a[0]


def getcurrentusername():
    '''
    Returns the username of the current user
    '''
    if 'USER' in os.environ:
        return os.environ['USER']      # Unix
    if 'USERNAME' in os.environ:
        return os.environ['USERNAME']  # Windows


def getsignals():
    ''' Return a dict of all available signals '''
    signallist = [
        'ABRT', 'CONT', 'IO', 'PROF', 'SEGV', 'TSTP', 'USR2', '_DFL', 'ALRM',
        'FPE', 'IOT', 'PWR', 'STOP', 'TTIN', 'VTALRM', '_IGN', 'BUS', 'HUP',
        'KILL', 'QUIT', 'SYS', 'TTOU', 'WINCH', 'CHLD', 'ILL', 'PIPE', 'RTMAX',
        'TERM', 'URG', 'XCPU', 'CLD', 'INT', 'POLL', 'RTMIN', 'TRAP', 'USR1',
        'XFSZ',
    ]
    signals = {}
    for signame in signallist:
        if hasattr(signal, 'SIG' + signame):
            signals[signame] = getattr(signal, 'SIG' + signame)
    return signals


def getuserhome():
    '''
    Returns the home-directory of the current user
    '''
    if 'HOME' in os.environ:
        return os.environ['HOME']      # Unix
    if 'HOMEPATH' in os.environ:
        return os.environ['HOMEPATH']  # Windows


def hasher(algorithm, argstr):
    def myhash(fd):
        h = hashlib.new(algorithm)
        with fd as f:
            h.update(f.read())
        return h.hexdigest()

    p = parseoptions()
    p.description = "Print or check {0} ".format(algorithm.upper()) +\
                    "checksums. With no FILE, or when FILE is -, read " +\
                    "standard input."
    p.usage = '%prog [OPTION]... FILE...'
    (opts, args) = p.parse_args(argstr.split())

    if len(args) == 0 or args == ['-']:
        yield myhash(sys.stdin) + '  -' + "\n"
    else:
        for arg in args:
            yield myhash(open(arg, 'rb')) + '  ' + arg + "\n"


def listcommands():
    '''
    Returns a list of all public commands
    '''
    l = []
    for cmd in _cmds:
        l.append(cmd.__name__)
    return l


def mode2string(mode):
    '''
    Convert mode-integer to string
    Example: 33261 becomes "-rwxr-xr-x"
    '''
    if stat.S_ISREG(mode):
        s = '-'
    elif stat.S_ISDIR(mode):
        s = 'd'
    elif stat.S_ISCHR(mode):
        s = 'c'
    elif stat.S_ISBLK(mode):
        s = 'b'
    elif stat.S_ISLNK(mode):
        s = 'l'
    elif stat.S_ISFIFO(mode):
        s = 'p'
    elif stat.S_ISSOCK(mode):
        s = 's'
    else:
        s = '-'

    # User Read
    if bool(mode & stat.S_IRUSR):
        s += 'r'
    else:
        s += '-'

    # User Write
    if bool(mode & stat.S_IWUSR):
        s += 'w'
    else:
        s += '-'

    # User Execute
    if bool(mode & stat.S_IXUSR):
        s += 'x'
    else:
        s += '-'

    # Group Read
    if bool(mode & stat.S_IRGRP):
        s += 'r'
    else:
        s += '-'

    # Group Write
    if bool(mode & stat.S_IWGRP):
        s += 'w'
    else:
        s += '-'

    # Group Execute
    if bool(mode & stat.S_IXGRP):
        s += 'x'
    else:
        s += '-'

    # Other Read
    if bool(mode & stat.S_IROTH):
        s += 'r'
    else:
        s += '-'

    # Other Write
    if bool(mode & stat.S_IWOTH):
        s += 'w'
    else:
        s += '-'

    # Other Execute
    if bool(mode & stat.S_IXOTH):
        s += 'x'
    else:
        s += '-'

    return s


def parseoptions():
    p = optparse.OptionParser(version=__version__, add_help_option=False)
    p.add_option("-h", "-?", "--help", action="store_true", dest='help',
                 help="show program's help message and exit")
    return p


def run(argv=sys.argv):
    '''
    Parse commandline arguments and run command.
    This is where the magic happens :-)

    :param argv:    List of arguments
    :return:        The exit status of the command. None means 0.
    '''
    commands = listcommands()
    commands.sort()

    if os.path.basename(argv[0]) in ['__init__.py', 'coreutils.py']:
        argv = argv[1:]

    p = optparse.OptionParser(version=__version__)
    p.disable_interspersed_args()  # Important!
    p.description = "Coreutils in Pure Python."
    p.usage = "%prog [OPTION]... [COMMAND]..."
    p.epilog = "Available Commands: " + ", ".join(commands)
    p.add_option("--createcommandlinks", dest="createcommanddirectory",
            help="Create a symlink to pycoreutils for every available command")
    p.add_option("--license", action="store_true", dest="license",
                 help="show program's license and exit")
    p.add_option("--runtests", action="store_true", dest="runtests",
            help="Run all sort of tests")
    (opts, args) = p.parse_args(argv)
    prog = p.get_prog_name()

    if argv == []:
        return p.print_help()

    if opts.license:
        return print(__license__)

    if opts.runtests:
        try:
            from pycoreutils import test
        except ImportError:
            print("Can't import pycoreutils.test. Please make sure to " +\
                  "include it in your PYTHONPATH", file=sys.stderr)
            sys.exit(1)
        return test.runalltests()

    if opts.createcommanddirectory:
        return createcommandlinks(prog, opts.createcommanddirectory)

    # Run the command
    errno = 0
    commandline = " ".join(args)
    try:
        output = runcommandline(commandline)
    except CommandNotFoundException as err:
        print(err, file=sys.stderr)
        print("Use {0} --help for a list of valid commands.".format(prog))
        errno = 2
    except StdOutException as err:
        print(err)
        errno = err.errno
    except StdErrException as err:
        print(err, file=sys.stderr)
        errno = err.errno
    except IOError as err:
        print("{0}: {1}: {2}".format(
              prog, err.filename, err.strerror), file=sys.stderr)
        errno = err.errno
    except OSError as err:
        print("{0}: {1}: {2}".format(
              prog, err.filename, err.strerror), file=sys.stderr)
        errno = err.errno
    except KeyboardInterrupt:
        errno = 0
    else:
        # Print the output
        if output:
            for out in output:
                print(out, end='')

    return errno


def runcommandline(commandline):
    '''
    Process a commandline

    :param commandline: String representing the commandline, i.e. "ls -l /tmp"
    '''
    return PyCoreutils().runcommandline(commandline)


def showbanner(width=None):
    '''
    Returns pycoreutils banner.
    The banner is centered if width is defined.
    '''
    subtext = "-= PyCoreutils version {0} =-".format(__version__)
    banner = [
        " ____  _  _  ___  _____  ____  ____  __  __  ____  ____  __    ___ ",
        "(  _ \( \/ )/ __)(  _  )(  _ \( ___)(  )(  )(_  _)(_  _)(  )  / __)",
        " )___/ \  /( (__  )(_)(  )   / )__)  )(__)(   )(   _)(_  )(__ \__ \\",
        "(__)   (__) \___)(_____)(_)\_)(____)(______) (__) (____)(____)(___/",
    ]

    if width:
        ret = ""
        for line in banner:
            ret += line.center(width) + "\n"
        ret += "\n" + subtext.center(width) + "\n"
        return ret
    else:
        return "\n".join(banner) + "\n\n" + subtext.center(68) + "\n"


def wsgierror(start_response, code, text, headers=[]):
    h = [(b'Content-Type', b'text/html')]
    h.extend(headers)
    start_response(b'{0} '.format(code), h)
    return [b'''<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML 2.0//EN"><html><head>
                <title>{code} {text}</title></head><body><h1>{code} {text}</h1>
                </body></html>'''.format(code=code, text=text)]


def wsgiserver(app, opts):
    '''
    Parse opts and return a WSGIServer running app
    '''
    # Set protocol version
    if opts.ssl_version:
        if opts.ssl_version == 'SSLv23':
            ssl_version = ssl.PROTOCOL_SSLv23
        elif opts.ssl_version == 'SSLv3':
            ssl_version = ssl.PROTOCOL_SSLv23
        elif opts.ssl_version == 'TLSv1':
            ssl_version = ssl.PROTOCOL_TLSv1

    # Authentication
    if opts.userlist:
        userdict = {}
        for x in opts.userlist:
            username, password = x.split(':', 1)
            userdict[username] = password
        app = WSGIAuth(app, userdict)

    server = WSGIServer((opts.address, opts.port),
                         certfile=opts.certfile,
                         keyfile=opts.keyfile,
                         ca_certs=opts.cafile,
                         ssl_version=ssl_version)
    server.set_app(app)
    return server


def wsgiserver_getoptions():
    '''
    Return an OptionParser with the options for wsgiserver
    '''
    p = parseoptions()
    p.epilog = "To enable https, you must supply a certificate file using " +\
               "'-c' and a key using '-k', both PEM-formatted. If both the " +\
               "certificate and the key are in one file, just use '-c'."
    p.add_option("-a", "--address", default="", dest="address",
            help="address to bind to")
    p.add_option("-c", "--certfile", dest="certfile",
            help="Use ssl-certificate for https")
    p.add_option("-p", "--port", default=8000, dest="port", type="int",
            help="port to listen to")
    p.add_option("-k", "--keyfile", dest="keyfile",
            help="Use ssl-certificate for https")
    p.add_option("-u", "--user", action="append", dest="userlist",
            help="Add a user for authentication in the form of " +\
                 "'USER:PASSWORD'. Can be specified multiple times.")
    p.add_option("-V", "--ssl-version", dest="ssl_version", default="SSLv23",
            help="Must be either 'SSLv23' (default), 'SSLv3', or 'TLSv1'")
    p.add_option("--cafile", dest="cafile",
            help="Authenticate remote certificate using CA certificate " +\
                 "file. Requires -c")
    return p


### EXCEPTIONS ##############################################################


class StdOutException(Exception):
    '''
    Raised when data is written to stdout
    '''
    def __init__(self, text, errno=1):
        '''
        :text:  Output text
        ;errno: Exit status of program
        '''
        self.text = text
        self.errno = errno

    def __str__(self):
        return self.text


class StdErrException(Exception):
    '''
    Raised when data is written to stderr
    '''
    def __init__(self, text, errno=2):
        '''
        :text:  Error text
        ;errno: Exit status of program
        '''
        self.text = text
        self.errno = errno

    def __str__(self):
        return self.text


class CommandNotFoundException(Exception):
    '''
    Raised when an unknown command is requested
    '''
    def __init__(self, prog):
        self.prog = prog

    def __str__(self):
        return "Command `{0}' not found.".format(self.prog)


class ExtraOperandException(StdErrException):
    '''
    Raised when an argument is expected but not found
    '''
    def __init__(self, program, operand, errno=1):
        '''
        :program:   Program that caused the error
        :operand:   Value of the extra operand
        ;errno: Exit status of program
        '''
        self.program = program
        self.operand = operand
        self.errno = errno

    def __str__(self):
        return "{0}: extra operand `{1}'. Try {0} --help' for more ".format(
                self.program, self.operand) + "information."


class MissingOperandException(StdErrException):
    '''
    Raised when an argument is expected but not found
    '''
    def __init__(self, program, errno=1):
        '''
        :program:   Program that caused the error
        ;errno: Exit status of program
        '''
        self.program = program
        self.errno = errno

    def __str__(self):
        return "{0}: missing operand. Try `{0} --help'".format(self.program) +\
               " for more information."


# Finally import all commands so addcommand() will register them
try:
    from pycoreutils.command import *
except ImportError:
    print("Can't import pycoreutils.command. Please make sure to " +\
          "include it in your PYTHONPATH", file=sys.stderr)
    sys.exit(1)


if __name__ == '__main__':
    sys.exit(run())
