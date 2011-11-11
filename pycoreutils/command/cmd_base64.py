# -*- coding: utf-8 -*-

# Copyright (c) 2009, 2010, 2011 Hans van Leeuwen.
# See LICENSE.txt for details.

from __future__ import print_function, unicode_literals
import pycoreutils
import base64 as _base64
import textwrap


def parseargs(p):
    '''
    Add arguments and `func` to `p`.

    :param p: ArgumentParser
    :return:  ArgumentParser
    '''
    p.set_defaults(func=func)
    p.description = "Base64 encode or decode FILE, or standard input, " + \
                    "to standard output."
    p.add_argument('file', nargs=1)
    p.add_argument("-d", action="store_true", dest="decode",
            help="decode data")
    p.add_argument("-w", dest="wrap", default=76, type=int,
            help="wrap encoded lines after COLS character (default 76). " + \
                 "Use 0 to disable line wrapping")
    return p


def func(args):
    s = ''
    for line, filename in pycoreutils.parsefilelist(args.FILE):
        s += line

    if args.decode:
        out = _base64.b64decode(s)
        if args.wrap == 0:
            print(out)
        else:
            for line in textwrap.wrap(out, args.wrap):
                print(line)
    else:
        out = _base64.b64encode(s)
        if args.wrap == 0:
            print(out)
        else:
            for line in textwrap.wrap(out, args.wrap):
                print(line)
