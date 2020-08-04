import sys
import os
import stat
import argparse
import glob
import tempfile
import py_compile
import zipfile
import shutil
import subprocess
import sysconfig
import re
import fnmatch
from os.path import join

parser = argparse.ArgumentParser()
parser.add_argument('--lldb_root', help='Root directory of LLDB build output')
parser.add_argument('--target', help='Build target triple')
parser.add_argument('--strip', default='strip', help='Name of the `strip` utility')
parser.add_argument('--release_package', action='store_true', help='Produce release package (deflate compression)')
parser.add_argument('output', help='Zip archive for LLDB package.')
parser.add_argument('debug_output', help='Zip archive for debug info, tools, etc.')
args = parser.parse_args()

stdlib_dir = str(sysconfig.get_path('stdlib'))

compression = zipfile.ZIP_DEFLATED if args.release_package else zipfile.ZIP_STORED
with tempfile.TemporaryDirectory() as temp_dir,\
     zipfile.ZipFile(args.output, 'w', compression=compression) as zip,\
     zipfile.ZipFile(args.debug_output, 'w', compression=compression) as debug_zip:

    if not args.release_package:
        debug_zip = None

    version_info = sys.version_info
    ver = version_info.major, version_info.minor

    def rel_glob(basedir, patterns):
        if type(patterns) is str:
            patterns = [patterns]
        return [(abspath, os.path.relpath(abspath, basedir))
                    for pattern in patterns 
                    for abspath in glob.glob(join(basedir, pattern), recursive=True)]

    stdlib_exclude = ['config-*', 'idlelib*', 'lib2to3*', 'site-packages*', 'test*', 'turtledemo*', 'tkinter*']

    def exclude(files, excludes):
        for abspath, relpath in files:
            if not any([fnmatch.fnmatch(relpath, exclude) for exclude in excludes]):
                yield abspath, relpath

    def exclude_lldb(files):
        for abspath, relpath in files:
            if not os.path.basename(relpath).startswith('_lldb.'):
                yield abspath, relpath

    pycfile = join(temp_dir, 'file.pyc')
    def compile_pyc(files):
        for abspath, relpath in files:
            py_compile.compile(abspath, pycfile)
            yield pycfile, relpath + 'c'

    tempbin = join(temp_dir, 'tempbin')
    def strip_binaries(files):
        if args.release_package:
            for abspath, relpath in files:
                shutil.copy(abspath, tempbin)
                subprocess.check_call([args.strip, tempbin])
                yield tempbin, relpath
        else:
            for abspath, relpath in files:
                yield abspath, relpath

    def rel_prefix(files, prefix):
        for abspath, relpath in files:
            yield abspath, join(prefix, relpath)

    def add_to_zip(files, zipfile):
        if zipfile is None:
            return
        for abspath, relpath in files:
            print('Adding ', relpath)
            zipfile.write(abspath, relpath)

    # Apply transforms to an iterator.  A transform must be eiather a callable or a tuple (callable, arg1, arg2, ...)
    def compose(it, *transforms):
        for transform in transforms:
            if type(transform) is tuple:
                fn, *args = transform
                it = fn(it, *args)
            else:
                it = transform(it)
        return it

    def inspect(files):
        for abspath, relpath in files:
            print('###', abspath, relpath)

    # lldb
    if '-linux-' in args.target: ########################################################################################################

        lldb_files = [
            'bin/lldb',
            'bin/lldb-argdumper',
            'bin/lldb-server',
            'lib/liblldb.*'
        ]
        files = rel_glob(args.lldb_root, lldb_files)
        add_to_zip(strip_binaries(files), zip)

        lldb_debug_files = [
            'bin/lldb',
            'bin/lldb-argdumper',
            'bin/lldb-server',
            'bin/llvm-dwarfdump',
            'bin/llvm-pdbutil',
            'bin/llvm-readobj',
            'lib/liblldb.*'
        ]
        files = rel_glob(args.lldb_root, lldb_files)
        add_to_zip(files, debug_zip)

        python_files = rel_glob(args.lldb_root, 'lib/lldb-python/**/*')
        compose(python_files, exclude_lldb, (add_to_zip, zip))

        # Python
        libpython = rel_glob(join('/usr/lib', args.target), 'libpython{}.{}*.so*'.format(*ver))
        libpython.sort(key=lambda x: len(x[1]), reverse=True)
        compose(libpython[:1], (rel_prefix, 'lib'), (add_to_zip, zip))

        pythonXY = 'lib/python{}.{}'.format(*ver)

        dylibs = rel_glob(stdlib_dir, 'lib-dynload/*' + args.target + '*')
        compose(dylibs, (rel_prefix, pythonXY), (add_to_zip, zip))

        stdlib_files = rel_glob(stdlib_dir, '**/*.py')
        compose(stdlib_files, (exclude, stdlib_exclude), compile_pyc, (rel_prefix, pythonXY), (add_to_zip, zip))

        # Other libs libpython depends upon
        other_libs = [
            'libexpat.so.1',
            'libz.so.1'
        ]
        files = rel_glob('/lib/{}'.format(args.target), other_libs)
        compose(files, (rel_prefix, 'lib'), (add_to_zip, zip))

    elif '-apple-' in args.target: ########################################################################################################

        # Fix install_name of Python in liblldb.dylib
        shutil.copy(join(args.lldb_root, 'lib/liblldb.dylib'), tempbin)
        output = subprocess.check_output(['otool', '-L', tempbin], encoding='utf8')
        regex = re.compile(r'^\s*(.*Python)\s', re.MULTILINE)
        match = regex.search(output)
        oldname = match.group(1)
        subprocess.check_call(['install_name_tool', '-change', oldname, '@rpath/Python', tempbin])
        add_to_zip([(tempbin, 'lib/liblldb.dylib')], zip)

        lldb_files = [
            'bin/lldb',
            'bin/lldb-argdumper',
            'bin/debugserver',
        ]
        files = rel_glob(args.lldb_root, lldb_files)
        add_to_zip(files, zip)
        for abspath, _ in files:
            dsymname = os.path.splitext(abspath)[0] + '.dSYM'
            subprocess.call(['dsymutil', abspath, '-o', dsymname])

        lldb_debug_files = [
            'bin/llvm-dwarfdump',
            'bin/llvm-pdbutil',
            'bin/llvm-readobj',
            'bin/lldb.dSYM/**/*',
            'bin/lldb-argdumper.dSYM/**/*',
            'bin/llvm-dwarfdump.dSYM/**/*',
            'bin/llvm-pdbutil.dSYM/**/*',
            'bin/llvm-readobj.dSYM/**/*',
            'lib/liblldb*.dSYM/**/*',
        ]
        add_to_zip(rel_glob(args.lldb_root, lldb_debug_files), debug_zip)

        python_files = rel_glob(args.lldb_root, 'lib/lldb-python/**/*')
        compose(python_files, exclude_lldb, (add_to_zip, zip))

        # Python
        shutil.copy(join(stdlib_dir, '../../Python'), tempbin)
        os.chmod(tempbin, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
        print(subprocess.check_output(['install_name_tool', '-id', '@rpath/Python', tempbin]))
        add_to_zip([(tempbin, 'lib/Python')], zip)

        pythonXY = 'lib/python{}.{}'.format(*ver)

        dylibs = rel_glob(stdlib_dir, 'lib-dynload/*')
        compose(dylibs, (rel_prefix, pythonXY), (add_to_zip, zip))

        stdlib_files = rel_glob(stdlib_dir, '**/*.py')
        compose(stdlib_files, (exclude, stdlib_exclude), compile_pyc, (rel_prefix, pythonXY), (add_to_zip, zip))

    elif '-windows-' in args.target: ########################################################################################################

        lldb_files = [
            'bin/lldb.exe',
            'bin/lldb-argdumper.exe',
            'bin/liblldb.dll',
            'lib/liblldb.lib',
        ]
        add_to_zip(rel_glob(args.lldb_root, lldb_files), zip)

        lldb_debug_files = [
            'bin/lldb.pdb',
            'bin/lldb-argdumper.pdb',
            'bin/llvm-dwarfdump.exe',
            'bin/llvm-dwarfdump.pdb',
            'bin/llvm-pdbutil.exe',
            'bin/llvm-pdbutil.pdb',
            'bin/llvm-readobj.exe',
            'bin/llvm-readobj.pdb',
            'bin/liblldb.pdb',
        ]
        add_to_zip(rel_glob(args.lldb_root, lldb_debug_files), debug_zip)

        python_files = rel_glob(args.lldb_root, 'lib/lldb-python/**/*')
        compose(python_files, exclude_lldb, (add_to_zip, zip))

        libpython = rel_glob(join(stdlib_dir, '..'), 'python3*.dll')
        compose(libpython, (rel_prefix, 'bin'), (add_to_zip, zip))

        dll_files = ['DLLs/*.pyd', 'DLLs/*.dll']
        dll_exclude = ['*/tcl*.dll', '*/tk*.dll']
        dlls = rel_glob(join(stdlib_dir, '..'), dll_files)
        compose(dlls, (exclude, dll_exclude), (add_to_zip, zip))

        stdlib_files = rel_glob(stdlib_dir, '**/*.py')
        compose(stdlib_files, (exclude, stdlib_exclude), compile_pyc, (rel_prefix, 'lib'), (add_to_zip, zip))

    else:
        raise Exception('Unknown target')
    
