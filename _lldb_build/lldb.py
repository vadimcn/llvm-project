from _lldb_build.target import TargetConfig
import os
import tempfile
import zipfile
import shutil
import re
from subprocess import call, check_call, check_output
from pathlib import Path
from os.path import join
from .utils import *


def package_lldb(lldb_root: Path, python_dist: Path, cfg: TargetConfig,
                 output_zip: Path, debug_output_zip: Path, release_package: bool = False):

    compression = zipfile.ZIP_DEFLATED if release_package else zipfile.ZIP_STORED
    with tempfile.TemporaryDirectory() as temp_dir,\
            zipfile.ZipFile(output_zip, 'w', compression=compression) as zip,\
            zipfile.ZipFile(debug_output_zip, 'w', compression=compression) as debug_zip:

        if not release_package:
            debug_zip = None

        def exclude_lldb(files: PathDuples):
            for abspath, relpath in files:
                if not os.path.basename(relpath).startswith('_lldb.'):
                    yield abspath, relpath

        tempbin = Path(temp_dir) / 'tempbin'

        def strip_binaries(files: PathDuples) -> PathDuples:
            if release_package:
                for abspath, relpath in files:
                    shutil.copy(abspath, tempbin)
                    check_call([cfg['CMAKE_STRIP'], tempbin])
                    yield tempbin, relpath
            else:
                for abspath, relpath in files:
                    yield abspath, relpath

        # lldb
        target_os = cfg['CMAKE_SYSTEM_NAME']
        if target_os == 'Linux':

            lldb_files = [
                'bin/lldb',
                'bin/lldb-argdumper',
                'bin/lldb-server',
                'lib/liblldb.*'
            ]
            files = rel_glob(lldb_root, lldb_files)
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
            files = rel_glob(lldb_root, lldb_files)
            add_to_zip(files, debug_zip)

            python_files = rel_glob(lldb_root, 'lib/lldb-python/**/*')
            compose(python_files, exclude_lldb, (add_to_zip, zip))

        elif target_os == 'Darwin':

            # Fix install_name of Python in liblldb.dylib
            shutil.copy(join(lldb_root, 'lib/liblldb.dylib'), tempbin)
            output = check_output(['otool', '-L', str(tempbin)], encoding='utf8')
            regex = re.compile(r'^\s*(.*(libpython3.*))\s\(', re.MULTILINE)
            match = regex.search(output)
            assert match is not None
            oldname = match.group(1)
            newname = '@rpath/' + match.group(2)
            check_call(['install_name_tool', '-change', oldname, newname, tempbin])
            add_to_zip([(tempbin, Path('lib/liblldb.dylib'))], zip)

            lldb_files = [
                'bin/lldb',
                'bin/lldb-argdumper',
                'bin/debugserver',
            ]
            files = rel_glob(lldb_root, lldb_files)
            add_to_zip(files, zip)
            for abspath, _ in files:
                dsymname = os.path.splitext(abspath)[0] + '.dSYM'
                call(['dsymutil', abspath, '-o', dsymname])

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
            add_to_zip(rel_glob(lldb_root, lldb_debug_files), debug_zip)

            python_files = rel_glob(lldb_root, 'lib/lldb-python/**/*')
            compose(python_files, exclude_lldb, (add_to_zip, zip))

        elif target_os == 'Windows':

            lldb_files = [
                'bin/lldb.exe',
                'bin/lldb-argdumper.exe',
                'bin/liblldb.dll',
                'lib/liblldb.lib',
            ]
            add_to_zip(rel_glob(lldb_root, lldb_files), zip)

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
            add_to_zip(rel_glob(lldb_root, lldb_debug_files), debug_zip)

            python_files = rel_glob(lldb_root, 'lib/lldb-python/**/*')
            compose(python_files, exclude_lldb, (add_to_zip, zip))

        else:
            raise Exception('Unknown target')

        # Python distro
        compose(rel_glob(python_dist, '**/*'), (add_to_zip, zip))
