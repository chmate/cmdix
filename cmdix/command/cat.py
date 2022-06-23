import sys


def parseargs(p):
    """
    Add arguments and `func` to `p`.

    :param p: ArgumentParser
    :return:  ArgumentParser
    """
    p.set_defaults(func=func)
    p.description = "Concatenate FILE(s), or standard input, " + "to standard output."
    p.add_argument('FILE', nargs='*')
    return p


def func(args):
    files = args.FILE if args.FILE else ["-"]

    for f in files:
        if f == "-":
            fp = sys.stdin.buffer
        else:
            fp = open(f, "rb")

        while True:
            line = fp.readline(1024 * 1024)
            sys.stdout.buffer.write(line)

            if not line:
                break
