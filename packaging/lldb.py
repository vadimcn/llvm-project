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
import re
import fnmatch
from os.path import join
from .utils import *

parser = argparse.ArgumentParser()
parser.add_argument('--lldb_root', help='Root directory of LLDB build output')
parser.add_argument('--python_dist', help='Python distro')
parser.add_argument('--target', help='Build target triple')
parser.add_argument('--strip', default='strip', help='Name of the `strip` utility')
parser.add_argument('--release_package', action='store_true', help='Produce release package (deflate compression)')
parser.add_argument('--output', help='Zip archive for LLDB package.')
parser.add_argument('--debug_output', help='Zip archive for debug info, tools, etc.')
args = parser.parse_args()

compression = zipfile.ZIP_DEFLATED if args.release_package else zipfile.ZIP_STORED
with tempfile.TemporaryDirectory() as temp_dir,\
     zipfile.ZipFile(args.output, 'w', compression=compression) as zip,\
     zipfile.ZipFile(args.debug_output, 'w', compression=compression) as debug_zip:

    if not args.release_package:
        debug_zip = None

    version_info = sys.version_info
    ver = version_info.major, version_info.minor

    def exclude_lldb(files):
        for abspath, relpath in files:
            if not os.path.basename(relpath).startswith('_lldb.'):
                yield abspath, relpath

    tempbin = Path(temp_dir) / 'tempbin'
    def strip_binaries(files: PathDuples) -> PathDuples:
        if args.release_package:
            for abspath, relpath in files:
                shutil.copy(abspath, tempbin)
                subprocess.check_call([args.strip, tempbin])
                yield tempbin, relpath
        else:
            for abspath, relpath in files:
                yield abspath, relpath

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

    elif '-apple-' in args.target: ########################################################################################################

        # Fix install_name of Python in liblldb.dylib
        shutil.copy(join(args.lldb_root, 'lib/liblldb.dylib'), tempbin)
        output = subprocess.check_output(['otool', '-L', tempbin], encoding='utf8')
        regex = re.compile(r'^\s*(.*(libpython3.*))\s\(', re.MULTILINE)
        match = regex.search(output)
        oldname = match.group(1)
        newname = '@rpath/' + match.group(2)
        subprocess.check_call(['install_name_tool', '-change', oldname, newname, tempbin])
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

    else:
        raise Exception('Unknown target')
    
    # Python distro
    compose(rel_glob(args.python_dist, '**/*'), (add_to_zip, zip))
