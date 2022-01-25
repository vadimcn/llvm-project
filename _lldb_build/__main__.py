import sys
import os
import argparse
import platform
from pathlib import Path
from glob import glob
import subprocess
from subprocess import check_call
from typing import Dict, Any
from .python import build_lldb_python
from .lldb import package_lldb
from .utils import out_of_date
from .target import TargetConfig, get_target_config

HOST_ARCH = platform.machine()


def dict_to_cmake(cmake_args: Dict[str, str]):
    return [f'-D{key}={val}' for key, val in cmake_args.items()]


def build_libxml2(work_dir: Path, cfg: TargetConfig):
    libxml2_src = work_dir / 'libxml2'
    if not libxml2_src.exists():
        check_call(['git', 'clone', '--branch=master', '--depth=1',
                    'https://github.com/GNOME/libxml2.git', str(libxml2_src)])

    libxml2_build = libxml2_src / 'build'
    libxml2_build.mkdir(exist_ok=True)
    libxml2_install = libxml2_src / 'install'
    libname = 'libxml2sd.lib' if cfg['CMAKE_SYSTEM_NAME'] == 'Windows' else 'libxml2.a'
    libxml2_lib = libxml2_install / 'lib' / libname

    if out_of_date([libxml2_lib], [libxml2_src / '*.c', libxml2_src / '*.h']):
        cmake_args = {
            'CMAKE_INSTALL_PREFIX': str(libxml2_install),
            'BUILD_SHARED_LIBS': 'OFF',
            'LIBXML2_WITH_SAX1': 'ON',
            'LIBXML2_WITH_THREADS': 'ON',
            # off
            'LIBXML2_WITH_C14N': 'OFF',
            'LIBXML2_WITH_CATALOG': 'OFF',
            'LIBXML2_WITH_DEBUG': 'OFF',
            'LIBXML2_WITH_DOCB': 'OFF',
            'LIBXML2_WITH_FTP': 'OFF',
            'LIBXML2_WITH_HTML': 'OFF',
            'LIBXML2_WITH_HTTP': 'OFF',
            'LIBXML2_WITH_ICONV': 'OFF',
            'LIBXML2_WITH_ICU': 'OFF',
            'LIBXML2_WITH_ISO8859X': 'OFF',
            'LIBXML2_WITH_LEGACY': 'OFF',
            'LIBXML2_WITH_LZMA': 'OFF',
            'LIBXML2_WITH_MEM_DEBUG': 'OFF',
            'LIBXML2_WITH_MODULES': 'OFF',
            'LIBXML2_WITH_OUTPUT': 'OFF',
            'LIBXML2_WITH_PATTERN': 'OFF',
            'LIBXML2_WITH_PROGRAMS': 'OFF',
            'LIBXML2_WITH_PUSH': 'OFF',
            'LIBXML2_WITH_PYTHON': 'OFF',
            'LIBXML2_WITH_READER': 'OFF',
            'LIBXML2_WITH_REGEXPS': 'OFF',
            'LIBXML2_WITH_RUN_DEBUG': 'OFF',
            'LIBXML2_WITH_SCHEMAS': 'OFF',
            'LIBXML2_WITH_SCHEMATRON': 'OFF',
            'LIBXML2_WITH_TESTS': 'OFF',
            'LIBXML2_WITH_THREAD_ALLOC': 'OFF',
            'LIBXML2_WITH_TREE': 'OFF',
            'LIBXML2_WITH_VALID': 'OFF',
            'LIBXML2_WITH_WRITER': 'OFF',
            'LIBXML2_WITH_XINCLUDE': 'OFF',
            'LIBXML2_WITH_XPATH': 'OFF',
            'LIBXML2_WITH_XPTR': 'OFF',
            'LIBXML2_WITH_ZLIB': 'OFF',
        }
        cmake_args.update(cfg)  # type: ignore

        cmake_args = dict_to_cmake(cmake_args)
        print('Configuring XML2 with:')
        for a in cmake_args:
            print(' ', a)

        check_call(['cmake', '-GNinja', str(libxml2_src), '-B', str(libxml2_build)] + cmake_args)
        check_call(['cmake', '--build', str(libxml2_build)])
        check_call(['cmake', '--build', str(libxml2_build), '--target', 'install'])

    return (libxml2_install / 'include/libxml2'), libxml2_lib


def build_swig(work_dir: Path, cfg: TargetConfig):
    swig_src = work_dir / 'swig'
    exename = 'swig' if 'win32' not in sys.platform else 'swig.exe'
    swig_exe = swig_src / exename
    if not swig_src.exists():
        check_call(['git', 'clone', '--branch=py3-stable-abi', '--depth=1',
                    'https://github.com/vadimcn/swig.git', str(swig_src)])
    if out_of_date([swig_exe], [swig_src / '*.c', swig_src / '*.h']):
        shell = cfg['CMAKE_SYSTEM_NAME'] == 'Windows'
        check_call(['bash', './autogen.sh'], shell=shell, cwd=str(swig_src))
        check_call(['bash', './configure', '--prefix=' + str(swig_src)], shell=shell, cwd=str(swig_src))
        check_call(['make'], cwd=str(swig_src))
    return swig_exe, swig_src


def build_lldb(work_dir: Path, cfg: TargetConfig, build_type: str, *,
               ccache: Path,
               libxml_inc: Path, libxml_lib: Path, swig_exe: Path, swig_dir: Path,
               python_exe: Path, python_inc: Path, python_lib: Path) -> Path:
    llvm_src = Path(__file__).resolve().parent.parent / 'llvm'
    llvm_build = work_dir / 'llvm'
    llvm_build.mkdir(exist_ok=True)

    cmake_args = {
        'CMAKE_BUILD_TYPE': build_type,
        'LLVM_ENABLE_PROJECTS': 'clang;libcxx;lldb',
        'LLVM_TARGETS_TO_BUILD': 'AArch64;ARM;AVR;MSP430;RISCV;X86;WebAssembly',
        'LLVM_PARALLEL_LINK_JOBS': '1',
        'LLVM_VERSION_SUFFIX': '-custom',
        'LLVM_APPEND_VC_REV': 'FALSE',
        'LLVM_ENABLE_TERMINFO': 'FALSE',
        'LLVM_ENABLE_LIBXML2': 'FORCE_ON',
        'LLDB_ENABLE_PYTHON': 'TRUE',
        'LLDB_EMBED_PYTHON_HOME': 'TRUE',
        'LLDB_PYTHON_HOME': '..',
        'LLDB_PYTHON_RELATIVE_PATH': 'lib/lldb-python',
        'LLDB_PYTHON_EXE_RELATIVE_PATH': 'python3',
        'LLDB_PYTHON_EXT_SUFFIX': '.so',
        'LLDB_ENABLE_LIBEDIT': 'FALSE',
        'LLDB_ENABLE_CURSES': 'FALSE',
        'LLDB_ENABLE_LZMA': 'FALSE',
        'Python3_EXECUTABLE': str(python_exe),
        'Python3_INCLUDE_DIRS': str(python_inc),
        'Python3_LIBRARIES': str(python_lib),
        'SWIG_EXECUTABLE': str(swig_exe),
        'SWIG_DIR': str(swig_dir),
        'LIBXML2_INCLUDE_DIR': str(libxml_inc),
        'LIBXML2_LIBRARY': str(libxml_lib),
    }

    if ccache is not None:
        cmake_args['CMAKE_C_COMPILER_LAUNCHER'] = str(ccache)
        cmake_args['CMAKE_CXX_COMPILER_LAUNCHER'] = str(ccache)

    cmake_args.update(cfg)  # type: ignore

    targets_to_build = ['lldb', 'llvm-dwarfdump', 'llvm-pdbutil', 'llvm-readobj']

    if cfg['CMAKE_SYSTEM_PROCESSOR'] != HOST_ARCH:
        cmake_args.update({
            'CMAKE_CROSSCOMPILING': 'ON',
            'CROSS_TOOLCHAIN_FLAGS_NATIVE': '-DLLVM_ENABLE_PROJECTS=clang'
        })

    if cfg['CMAKE_SYSTEM_NAME'] == 'Linux':
        targets_to_build += ['lldb-server']
        cmake_args.update({
            'CMAKE_EXE_LINKER_FLAGS': cmake_args.get('CMAKE_EXE_LINKER_FLAGS', '') + ' -L' + str(python_lib.parent),
            'CMAKE_SHARED_LINKER_FLAGS': cmake_args.get('CMAKE_SHARED_LINKER_FLAGS', '') + ' -L' + str(python_lib.parent),
            'LLVM_ENABLE_ZLIB': 'FORCE_ON'
        })

    if cfg['CMAKE_SYSTEM_NAME'] == 'Darwin':
        cmake_args.update({
            'LLDB_USE_SYSTEM_DEBUGSERVER': 'ON',
            'LLVM_ENABLE_ZLIB': 'FORCE_ON'
        })

    if cfg['CMAKE_SYSTEM_NAME'] == 'Windows':
        cmake_args.update({
            'CMAKE_C_FLAGS': '-DLIBXML_STATIC=1',
            'CMAKE_CXX_FLAGS': '-DLIBXML_STATIC=1'
        })

    cmake_args = dict_to_cmake(cmake_args)
    print('Configuring LLVM with:')
    for a in cmake_args:
        print(' ', a)

    os.environ['SWIG_LIB'] = str(swig_dir / 'Lib')
    os.environ['PATH'] = str(python_exe.parent) + os.pathsep + os.environ['PATH']

    check_call(['cmake', '-GNinja', str(llvm_src), '-B', str(llvm_build)] + cmake_args)

    for target in targets_to_build:
        print('Building', target)
        check_call(['cmake', '--build', str(llvm_build), '--target', target])

    return llvm_build


def main(args: Any):
    work_dir = args.build_dir.resolve()
    cfg = get_target_config(args.target)

    target_python_archive = cfg.get('TARGET_PYTHON_ARCHIVE')
    if target_python_archive is None:
        python_dist = work_dir / 'python'
    else:
        python_dist = work_dir / 'python_dist'
        if not python_dist.exists():
            cpython_archive = glob(str(args.python_standalone / target_python_archive))[0]
            python_dist.mkdir(exist_ok=True)
            zstd = subprocess.Popen(['zstd', '-dcf', cpython_archive], stdout=subprocess.PIPE)
            check_call(['tar', '--strip-components=1', '-xf', '-'], stdin=zstd.stdout, cwd=str(python_dist))

    print('Using python_dist:', python_dist)
    python_lldb = work_dir / 'python_lldb'
    python_exe = Path(sys.executable)
    python_inc, python_lib = build_lldb_python(python_dist, python_lldb, cfg)

    libxml_inc, libxml_lib = build_libxml2(work_dir, cfg)

    swig_exe, swig_dir = build_swig(work_dir, cfg)

    lldb_root = build_lldb(work_dir, cfg, args.build_type,
                           ccache=args.ccache,
                           libxml_inc=libxml_inc, libxml_lib=libxml_lib,
                           swig_exe=swig_exe, swig_dir=swig_dir,
                           python_exe=python_exe, python_inc=python_inc, python_lib=python_lib)

    lldb_archive = work_dir / f'lldb--{args.target}.zip'
    lldb_debug_archive = work_dir / f'lldb-debug{args.target}.zip'

    package_lldb(lldb_root, python_lldb, cfg, lldb_archive, lldb_debug_archive, release_package=args.release_package)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', required=True)
    parser.add_argument('--python-standalone', type=Path, required=True)
    parser.add_argument('--build-dir', type=Path, default='.')
    parser.add_argument('--build-type', default='MinSizeRel')
    parser.add_argument('--release-package', action='store_true')
    parser.add_argument('--ccache', type=Path)
    args = parser.parse_args()
    main(args)
