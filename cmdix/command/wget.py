#!/usr/bin/env python3

import os.path
from urllib.request import Request, urlopen
from urllib.parse import urlsplit


def parseargs(p):
    p.set_defaults(func=func)
    p.description = "Download of files from the Internet"
    p.add_argument("url", nargs="+", help="write documents to FILE.")
    p.add_argument("-O", "--output-document", help="write documents to FILE.")
    return p


def func(args):
    if args.output_document:
        with open(args.output_document, 'wb') as fout:
            fout.write(b'')

    for url in args.url:
        if args.output_document:
            dst = args.output_document
            mode = 'ab'
        else:
            surl = urlsplit(url)
            dst = os.path.basename(surl.path)
            mode = 'wb'

        req = Request(url)
        with urlopen(req) as fin:
            length = fin.headers.get('content-length', None)
            print("Getting {} bytes from {} ...".format(length, url))
            print("Save to {}".format(dst))
            with open(dst, mode) as fout:

                while 1:
                    din = fin.read(1024 * 1024)
                    if not din:
                        break
                    fout.write(din)

        print("Done")
