#!/usr/bin/env python3
"""Sets up an improvised .pc file that refers to a Siesta OBJ directory.
ONLY use this functionality if you don't have the ability to properly install
a libsiesta and pkgconf file.
You must have already built Siesta in the Obj directory (and not cleaned up).
"""
import subprocess as sp
from pathlib import Path
import argparse


PKGCONF_TEXT = """
Name: {name}
Description: Improper pkgconf-file. Links to a custom Siesta Obj dir.
Version: {version}
Libs: {lpaths} {libs}
Cflags: {includes}
"""


def group_make_commands(lines):
    if isinstance(lines, str):
        lines = lines.splitlines()
    commands = []
    cur_cmd = []
    for l in lines:
        l = l.strip()
        continues = l.endswith("\\")
        cur_cmd.append(l[:-1] if continues else l)
        if not continues:
            commands.append(" ".join(cur_cmd))
            cur_cmd = []
    return commands


def abs_relative_dir(base, rel):
    rel = Path(rel)
    if not rel.root:
        return str((Path(base) / rel).resolve())
    return rel


def get_strings_lstripped(strings, *lstrip):
    ret = []
    for start in lstrip:
        for s in strings:
            if s.startswith(start):
                ret.append(s[len(start) :])
    return ret


def get_include_args(objdir):
    """Get the include args. 
    Use the stuff to do with siesta.F to obtain these args."""
    p = sp.run("make --dry-run siesta.o", shell=True, text=True, stdout=sp.PIPE, check=True, cwd=objdir)
    commands = group_make_commands(p.stdout)
    siesta_cmd = next(c for c in commands if "siesta.F" in c and "-c " in c)
    args = siesta_cmd.split()
    return [abs_relative_dir(objdir, inc) for inc in get_strings_lstripped(args, "-I")]


def get_link_args(objdir):
    p = sp.run("make --dry-run siesta", shell=True, text=True, stdout=sp.PIPE, check=True, cwd=objdir)
    commands = group_make_commands(p.stdout)
    siesta_cmd = next(c for c in commands if "-o siesta" in c)
    args = siesta_cmd.split()
    lpaths = [abs_relative_dir(objdir, p) for p in get_strings_lstripped(args, "-L", "-Wl,rpath=")]
    libs = get_strings_lstripped(args, "-l")
    return lpaths, libs


def manual_create_libsiesta(objdir):
    """For use with versions of Siesta that don't create the libsiesta.a file"""
    libsiesta_tn = Path("libsiesta_thin_nested.a")
    libsiesta = Path("libsiesta.a")
    for l in (libsiesta_tn, libsiesta):
        pl = objdir / l
        if pl.exists():
            raise ValueError(pl, "already exists!")

    compiled_files = list(objdir.glob("*.o")) + list(objdir.glob("*.a"))
    compiled_files = list(map(str, compiled_files))
    sp.run(["ar", "rcsT", str(libsiesta_tn)] + compiled_files, check=True, cwd=objdir)
    sp.run(
        ["ar", "-M"],
        text=True,
        input=f"CREATE {libsiesta!s}\nADDLIB {libsiesta_tn!s}\nSAVE\nEND",
        check=True,
        cwd=objdir,
    )
    sp.run(["ranlib", str(libsiesta)], check=True, cwd=objdir)


def render_pkg_config(name, version, lpaths, libs, includes):
    return PKGCONF_TEXT.format(
        name=name,
        version=version,
        lpaths=" ".join(f"-L{p}" for p in lpaths),
        libs=" ".join(f"-l{lib}" for lib in libs),
        includes=" ".join(f"-I{p}" for p in includes),
    )


def get_parser():
    parser = argparse.ArgumentParser(usage=__doc__)
    a = parser.add_argument
    a("objdir", type=Path, help="The Siesta OBJ dir where you have already build Siesta.")
    a(
        "--pkgdir",
        type=Path,
        default=Path(),
        help="Where to put the generated pkg-conf. Defaults to working directory.",
    )
    a(
        "--create-libsiesta",
        action="store_true",
        help=(
            "Some versions of Siesta don't make the libsiesta.a. Use this option to run the archiver to make the lib."
        ),
    )
    return parser


if __name__ == "__main__":
    args = get_parser().parse_args()
    abs_obj = args.objdir.resolve()

    includes = get_include_args(abs_obj)
    includes.append(str(abs_obj))

    lpaths, libs = get_link_args(abs_obj)
    lpaths.append(str(abs_obj))
    libs.append("siesta")

    if args.create_libsiesta:
        print("Creating libsiesta.a in", abs_obj, "...")
        manual_create_libsiesta(abs_obj)

    pcfile = args.pkgdir / "Siesta.pc"
    pcfile.write_text(render_pkg_config("Siesta", "4.2", lpaths, libs, includes))

    print(
        f"Wrote a pkgconf file to {pcfile}. You can now use"
        f"\n $PKG_CONFIG_PATH={pcfile.parent.resolve()!s}:$PKG_CONFIG_PATH"
        f" pip3 install {Path(__file__).resolve()!s}\nto install PSiesta."
        "\nIt might be advantageous to use --no-build-isolation (it's a bunch faster!)."
        "\nIf you are compiling with MPI, you must use CC=mpicc FC=mpifort (or whichever appropriate for your"
        " compiler suite), as this script can't auto-setup this for you."
    )
