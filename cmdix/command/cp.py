import os
import os.path
import shutil

from .. import exception


def parseargs(p):
    """
    Add arguments and `func` to `p`.

    :param p: ArgumentParser
    :return:  ArgumentParser
    """
    p.set_defaults(func=func)
    p.description = "Copy SOURCE to DEST, or multiple SOURCE(s) to DIRECTORY."
    p.add_argument('SOURCE', nargs='+')
    p.add_argument('DEST', nargs=1)
    p.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        dest="interactive",
        help="prompt before overwrite",
    )
    p.add_argument(
        "-p",
        "--preserve",
        action="store_true",
        dest="preserve",
        help="preserve as many attributes as possible",
    )
    p.add_argument(
        "-r",
        "-R",
        "--recursive",
        action="store_true",
        dest="recursive",
        help="copy directories recursively",
    )
    p.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        dest="verbose",
        help="print a message for each created directory",
    )
    return p


def func(args):
    dst = args.DEST[0]
    for src in args.SOURCE:
        if os.path.isdir(dst):
            dst = os.path.join(dst, os.path.basename(src))
        handle(args, src, dst)


def handle(args, src, dst):
    if args.verbose:
        print("'{}' -> '{}'".format(src, dst))

    # Set the _copy function
    if args.preserve:
        _copy = shutil.copy2
        symlinks = True
    else:
        _copy = shutil.copy
        symlinks = False

    if args.recursive:
        if os.path.isdir(src):
            shutil.copytree(
                src, dst, symlinks=symlinks, copy_function=_copy, dirs_exist_ok=True
            )
        else:
            _copy(src, dst)
    else:
        _copy(src, dst)
