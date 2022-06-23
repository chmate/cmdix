import ast


def parseargs(p):
    """
    Add arguments and `func` to `p`.

    :param p: ArgumentParser
    :return:  ArgumentParser
    """
    p.set_defaults(func=func)
    p.description = "display a line of text"

    p.add_argument("-n", action="store_true", help="do not output the trailing newline")
    p.add_argument(
        "-e",
        action="store_true",
        dest="escape",
        help="enable interpretation of backslash escapes",
    )
    p.add_argument(
        "-E",
        action="store_false",
        dest="escape",
        help="disable interpretation of backslash escapes (default)",
    )
    p.add_argument('string', nargs='*')

    return p


def escape(s):
    s = s.split("'")
    x = [ast.literal_eval("'{}'".format(i)) for i in s]

    return "'".join(x)


def func(args):
    sep = ""
    for s in args.string:
        if args.escape:
            s = escape(s)
        print("{}{}".format(sep, s), end="")
        sep = " "

    if not args.n:
        print("")
