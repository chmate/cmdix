from .. import lib
import os
import stat
import time


class ParseArgs:
    conflict_handler = 'resolve'

    def __call__(self, p):
        """
        Add arguments and `func` to `p`.

        :param p: ArgumentParser
        :return:  ArgumentParser
        """
        # TODO: Show user and group names in ls -l, correctly format dates in ls -l
        p.add_help = False
        p.set_defaults(func=func)
        p.description = (
            "List information about the FILEs (the current "
            + "directory by default). Sort entries "
            + "alphabetically if none of -cftuvSUX nor --sort."
        )
        p.add_argument('FILE', nargs="*")
        p.add_argument(
            "-l", "--longlist", action="store_true", help="use a long listing format"
        )
        p.add_argument(
            "-h",
            "--human-readable",
            action="store_true",
            help="with -l print sizes like 1K 234M 2G etc.",
        )
        return p


parseargs = ParseArgs()


def div_round_closest(x, divisor):
    if (x - 1) <= 0 or (divisor - 1) <= 0:
        return 0

    return (
        (x + (divisor // 2)) // divisor
        if ((x > 0) == (divisor > 0))
        else (x - (divisor // 2)) // divisor
    )


def human_size(size):
    S_KiB = 1024
    S_MiB = S_KiB * 1024
    S_GiB = S_MiB * 1024

    scale = 16

    if size > scale * S_GiB:
        return '{:,d} GiB'.format(div_round_closest(size, S_GiB))
    if size > scale * S_MiB:
        return '{:,d} MiB'.format(div_round_closest(size, S_MiB))
    if size > scale * S_KiB:
        return '{:,d} KiB'.format(div_round_closest(size, S_KiB))

    return '{:,d} B'.format(size)


def func(args):
    filelist = args.FILE
    if not args.FILE:
        filelist = ['.']

    for arg in filelist:
        dirlist = os.listdir(arg)
        dirlist.sort()
        ell = []
        sizelen = 0  # Length of the largest filesize integer
        nlinklen = 0  # Length of the largest nlink integer
        for f in dirlist:
            path = os.path.join(arg, f)
            if not args.longlist:
                print(f)
            else:
                st = os.lstat(path)
                mode = lib.mode2string(st.st_mode)
                nlink = st.st_nlink
                uid = st.st_uid
                gid = st.st_gid
                size = st.st_size
                if args.human_readable:
                    size = human_size(size)

                mtime = time.localtime(st.st_mtime)
                if stat.S_ISLNK(st.st_mode):
                    f += " -> {0}".format(os.readlink(path))
                ell.append((mode, nlink, uid, gid, size, mtime, f))

                # Update sizelen
                _sizelen = len(str(size))
                if _sizelen > sizelen:
                    sizelen = _sizelen

                # Update nlinklen
                _nlinklen = len(str(nlink))
                if _nlinklen > nlinklen:
                    nlinklen = _nlinklen

        for mode, nlink, uid, gid, size, mtime, f in ell:
            modtime = time.strftime('%Y-%m-%d %H:%m', mtime)
            print(
                "{0} {1:>{nlink}} {2:<5} {3:<5} {4:>{size}} {5} {6}".format(
                    mode,
                    nlink,
                    uid,
                    gid,
                    size,
                    modtime,
                    f,
                    size=sizelen,
                    nlink=nlinklen,
                )
            )
