from __future__ import print_function, unicode_literals
from ..exception import StdErrException
import os

from .. import onlyunix

try:
    import pwd
except ImportError:
    pass


@onlyunix
def parseargs(p):
    '''
    Add arguments and `func` to `p`.

    :param p: ArgumentParser
    :return:  ArgumentParser
    '''
    # TODO: Support for groups and --reference
    p.set_defaults(func=func)
    p.description = (
        "Change the owner and/or group of each FILE to OWNER "
        + "and/or GROUP. With --reference, change the owner and"
        + " group of each FILE to those of RFILE."
    )
    p.add_argument('FILE', nargs='*')
    p.add_argument('owner', nargs='?')
    return p


def func(args):
    if not args.owner:
        try:
            user = pwd.getpwnam(args.owner)
        except KeyError:
            raise StdErrException(
                "{0}: invalid user: '{1}'".format(args.prog, args.owner)
            )
        uid = user.pw_uid

    for arg in args.FILE:
        os.chown(arg, int(uid), -1)
