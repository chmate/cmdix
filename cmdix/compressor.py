import bz2
import gzip
import os
import shutil
import sys

from .exception import StdOutException, StdErrException


def compressor(p, comptype='gzip', decompress=False):
    """
    Handles compression and decompression as bzip2 and gzip
    """
    p.description = (
        "Compress or uncompress FILE (by default, compress " + "FILE in-place)."
    )
    p.set_defaults(func=compressorfunc, comptype=comptype, decompress=decompress)
    p.add_argument('FILE', nargs='*')
    p.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Force compression or decompression even if the file already exists",
    )
    p.add_argument(
        "-c",
        "--stdout",
        "--as-stdout",
        action="store_true",
        dest="stdout",
        help="write on standard output, keep original files unchanged",
    )
    p.add_argument(
        "-C",
        "--compresslevel",
        dest="compresslevel",
        type=int,
        default=6,
        help="set file mode (as in chmod), not a=rwx - umask",
    )
    p.add_argument(
        "-d", "--decompress", action="store_true", dest="decompress", help="decompress"
    )
    p.add_argument(
        "-1",
        "--fast",
        action="store_const",
        dest="compresslevel",
        const=1,
        help="Use the fastest type of compression",
    )
    p.add_argument(
        "-2",
        action="store_const",
        dest="compresslevel",
        const=2,
        help="Use compression level 2",
    )
    p.add_argument(
        "-3",
        action="store_const",
        dest="compresslevel",
        const=3,
        help="Use compression level 3",
    )
    p.add_argument(
        "-4",
        action="store_const",
        dest="compresslevel",
        const=4,
        help="Use compression level 4",
    )
    p.add_argument(
        "-5",
        action="store_const",
        dest="compresslevel",
        const=5,
        help="Use compression level 5",
    )
    p.add_argument(
        "-6",
        action="store_const",
        dest="compresslevel",
        const=6,
        help="Use compression level 6",
    )
    p.add_argument(
        "-7",
        action="store_const",
        dest="compresslevel",
        const=7,
        help="Use compression level 7",
    )
    p.add_argument(
        "-8",
        action="store_const",
        dest="compresslevel",
        const=8,
        help="Use compression level 8",
    )
    p.add_argument(
        "-9",
        "--best",
        action="store_const",
        dest="compresslevel",
        const=9,
        help="Use the best type of compression",
    )
    return p


def compressorfunc(args):
    if args.comptype == 'gzip':
        compresstype = gzip.GzipFile
        suffix = '.gz'
    elif args.comptype == 'bzip2':
        compresstype = bz2.BZ2File
        suffix = '.bz2'

    infiles = args.FILE

    # Use stdin for input if no file is specified or file is '-'
    if not len(args.FILE):
        infiles = ['-']

    for infile in infiles:
        f = decompress if args.decompress else compress
        fpin, fpout = f(args, compresstype, infile, suffix)

        shutil.copyfileobj(fpin, fpout)


def compress(args, compresstype, infile, suffix):
    zippath = infile + suffix
    fileobj = None
    mode = "wb" if args.force else "xb"

    if len(args.FILE) == 0 or args.stdout:
        zippath = ""
        fileobj = sys.stdout.buffer

    if infile == '-':
        fpin = sys.stdin.buffer
    else:
        fpin = open(infile, 'rb')

    fpout = compresstype(
        zippath, mode, compresslevel=args.compresslevel, fileobj=fileobj
    )

    return fpin, fpout


def decompress(args, compresstype, infile, suffix):
    fileobj = None

    if infile == '-':
        fileobj = sys.stdin.buffer
        infile = None

    mode = "wb" if args.force else "xb"

    fpin = compresstype(
        infile, mode='rb', compresslevel=args.compresslevel, fileobj=fileobj
    )

    if len(args.FILE) == 0 or args.stdout or fileobj is not None:
        fpout = sys.stdout.buffer
    else:
        unzippath = infile.rstrip(suffix)

        fpout = open(unzippath, mode)

    return fpin, fpout
