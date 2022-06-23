import os
import platform
import getpass

try:
    import pwd
except ImportError:
    pass


def parseargs(p):
    """
    Add arguments and `func` to `p`.

    :param p: ArgumentParser
    :return:  ArgumentParser
    """
    p.set_defaults(func=func)
    p.description = (
        "Print the user name associated with the current"
        + "effective user ID.\nSame as id -un."
    )
    return p


def func(args):
    if platform.system() == 'Windows':
        print(getpass.getuser())
    else:
        print(pwd.getpwuid(os.getuid())[0])
