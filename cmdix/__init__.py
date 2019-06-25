from __future__ import print_function, unicode_literals
import sys

import argparse
import os
import shlex

import importlib_metadata
import importlib_resources

try:
    import pathlib
except ImportError:
    import pathlib2 as pathlib

from . import command
from .exception import CommandNotFoundException


__version__ = importlib_metadata.version(__name__)


def onlyunix(f):
    '''
    Decorator that indicates that the command cannot be run on windows
    '''
    f._onlyunix = True
    return f


def format_all_help():
    '''
    Yields (commandname, commandhelp) for all available commands.
    '''
    for commandname in listcommands():
        cmd = getcommand(commandname)
        p = cmd(argparse.ArgumentParser(prog=commandname))
        yield (commandname, p.format_help())


def getcommand(commandname):
    '''
    Returns the `parseargs`-function of the given commandname.
    Raises a CommandNotFoundException if the command is not found
    '''
    # Try to import the command module
    importstring = 'cmdix.command.{0}'.format(commandname)
    try:
        parseargs = __import__(importstring, fromlist=1).parseargs
    except ImportError:
        raise CommandNotFoundException(commandname)

    # Check if the command is available on Windows
    if os.name == 'nt':
        try:
            parseargs._onlyunix
        except AttributeError:
            pass
        else:
            raise CommandNotFoundException(commandname)

    return parseargs


def listcommands():
    '''
    Returns a list of all available commands
    '''
    paths = map(pathlib.Path, importlib_resources.contents(command))
    return (path.stem for path in paths if not path.name.startswith('_'))


def _gen_script_definitions():
    print('console_scripts =')
    for cmd in listcommands():
        print('\t{cmd} = cmdix:run'.format(**locals()))


def run(argv=None):
    '''
    Parse commandline arguments and run command.
    If argv is None, read from sys.argv.

    For example:

    >>> import cmdix
    >>> cmdix.run(['seq', '-s', ' to the ', '1', '4'])
    1 to the 2 to the 3 to the 4

    :param argv:    List of arguments
    :return:        The exit status of the command. None means 0.
    '''
    argv = argv or sys.argv
    commandname = os.path.basename(argv.pop(0))
    parser = argparse.ArgumentParser(
        add_help=False,
        description="Coreutils in Pure Python.",
        prog=commandname,
        epilog="Available Commands: " + ", ".join(listcommands()),
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("command", nargs="?")
    group.add_argument(
        "--allhelp", action="store_true", help="Show the help pages off all commands"
    )
    group.add_argument(
        "--license", action="store_true", help="Show program's license and exit"
    )
    group.add_argument("--runtests", action="store_true", help="Run all sort of tests")

    if commandname in ('__main__.py',):
        args, argv = parser.parse_known_args(argv)

        if args.license:
            print("MIT")
            return

        elif args.allhelp:
            for commandname, commandhelp in format_all_help():
                print("\n" + commandname + "\n\n" + commandhelp)
            return

        elif args.runtests:
            try:
                from . import test
            except ImportError:
                print("Can't import test suite", file=sys.stderr)
                sys.exit(1)
            test.runalltests()
            return

        elif not args.command and not argv:
            parser.print_help()
            return

        commandname = args.command

    # Run the subcommand
    try:
        cmd = getcommand(commandname)
    except CommandNotFoundException:
        print("Command `{0}` not found.".format(commandname), file=sys.stderr)
        return
    p = cmd(argparse.ArgumentParser(prog=commandname))
    args = p.parse_args(argv)
    args.func(args)


def runcommandline(commandline):
    '''
    Process a commandline; main entry-point.

    Examples:

    >>> import cmdix
    >>> cmdix.runcommandline('basename /foo/bar/')
    bar
    >>> cmdix.runcommandline('cal 2 2000')
       February 2000
    Su Mo Tu We Th Fr Sa
           1  2  3  4  5
     6  7  8  9 10 11 12
    13 14 15 16 17 18 19
    20 21 22 23 24 25 26
    27 28 29

    :param commandline: String representing the commandline, i.e. "ls -l /tmp"
    '''
    return run(shlex.split(str(commandline)))
