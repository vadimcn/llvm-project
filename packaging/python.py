import os
import argparse
import py_compile
import subprocess
import json
import tempfile
from itertools import chain
from pathlib import Path
from .utils import *

pycfile = Path(tempfile.gettempdir()) / 'file.pyc'
def compile_pyc(files):
    for abspath, relpath in files:
        py_compile.compile(abspath,str(pycfile))
        yield pycfile, str(relpath) + 'c'

def main(args):
    shutil.rmtree(args.output)

    manifest = json.load(open(args.python_dist / 'PYTHON.json'))
    extensions = manifest['build_info']['extensions']

    def should_include(name, ext):
        if ext['required']:
            return True
        if name in ['_ctypes', '_ssl', '_scproxy', 'zlib']: # Needed for codelldb or pip.
            return True
        allowed_libs = ['intl', 'iconv'] # For some reason these are linked to most extensions on Mac.
        extra_libs = [lib for lib in ext.get('links', []) if lib['name'] not in allowed_libs]
        return len(extra_libs) == 0 # Don't want any other external lib dependencies.

    included_ext = { name: variants[0] for name, variants in extensions.items() if should_include(name, variants[0]) }
    print('Included extensions:', list(included_ext.keys()))

    stdlib_src =  manifest['python_paths']['stdlib']
    if stdlib_src.startswith('..'): # Bug in python-standalone for cross-builds
        pos = stdlib_src.index('install')
        stdlib_src = stdlib_src[pos:]
    stdlib_src = args.python_dist / stdlib_src
    stdlib_dist = args.output / 'lib' if 'windows' in args.target else args.output / 'lib' / 'python3.8'

    stdlib_files = rel_glob(stdlib_src, ['**/*.py', '**/*.pth', '**/*.pem'])
    stdlib_exclude = ['config-*', 'idlelib/*', 'lib2to3/*', 'test/*', 'turtledemo/*', 'tkinter/*', 'curses/*', 'sqlite3/*']
    compose(stdlib_files, (exclude, stdlib_exclude), (copy_to, stdlib_dist))

    if 'linux' in args.target or 'darwin' in args.target:
        # Create config.o with _PyImport_Inittab
        with open('config.c', 'w') as config:
            config.write('#include "Python.h"\n')

            for name, ext in included_ext.items():
                init_fn = ext['init_fn']
                if init_fn != 'NULL':
                    config.write('extern PyObject* {}(void);\n'.format(init_fn))

            config.write('struct _inittab _PyImport_Inittab[] = {\n')
            for name, ext in included_ext.items():
                init_fn = ext.get('init_fn')
                config.write('    {{ "{}", {} }},\n'.format(name, init_fn))
            config.write('    { 0, 0 }\n')
            config.write('};\n')

        subprocess.run([args.cc, '-I', args.python_dist / 'install' / 'include' / 'python3.8', 
                                '-c', 'config.c'])

        # Create libpythonXY.so
        objects = chain.from_iterable([manifest['build_info']['core']['objs']] + [ext['objs'] for ext in included_ext.values()])
        inittab_object = manifest['build_info']['inittab_object']
        objects = ['config.o'] + [str(args.python_dist / obj) for obj in objects if obj != inittab_object]
        objects = list(set(objects)) # Deduplicate
        subprocess.run([args.ar, '-r', 'libpython.a'] + objects)

        libs = ['libpython.a']
        for lib in (lib for ext in included_ext.values() for lib in ext['links']):
            if lib.get('system'):
                libs.append('-l' + lib['name'])
            elif lib.get('framework'):
                libs.append('-Wl,-framework,' + lib['name'])
            else: 
                libs.append(args.python_dist / lib['path_static'])

        os.makedirs(args.output / 'lib', exist_ok=True)

        if 'linux' in args.target:
            with open('python.exports', 'w') as exports:
                exports.write('libpython38.so\n{\nglobal:\nPy*;_Py*;__Py*;\nlocal:\n*;\n};\n')

            libs += ['-lpthread', '-lm', '-lutil']
            python_dylib = args.output / 'lib' / 'libpython38.so'
            cmd = [args.cc, '-shared', 
                            '-Wl,--no-undefined',
                            '-Wl,--version-script,python.exports',
                            '-o', python_dylib] + objects + ['-Wl,-('] + libs + ['-Wl,-)']
            subprocess.run(cmd)
            subprocess.run([args.strip, python_dylib])
        else:
            with open('python.exports', 'w') as exports:
                exports.write('Py*\n_Py*\n__Py*\n')

            python_dylib = args.output / 'lib' / 'libpython38.dylib'
            cmd = [args.cc, '-shared',
                            '-Wl,-exported_symbols_list,python.exports',
                            '-o', python_dylib] + objects + libs
            subprocess.run(cmd)

    elif 'windows' in args.target:
        python_dll = args.python_dist / manifest['build_info']['core']['shared_lib']
        os.makedirs(args.output / 'bin')
        shutil.copy(python_dll, args.output / 'bin')
        shutil.copy(python_dll.parent / 'python3.dll', args.output / 'bin')

        os.makedirs(args.output / 'DLLs')
        for name, ext in included_ext.items():
            dylib = ext.get('shared_lib')
            if dylib:
                shutil.copy(args.python_dist / dylib, args.output / 'DLLs')
            for lib in ext.get('links', []):
                dylib = lib.get('path_dynamic')
                if dylib:
                    shutil.copy(args.python_dist / dylib, args.output / 'DLLs')

parser = argparse.ArgumentParser()
parser.add_argument('--python_dist', help='Python-standalone distribution root', type=Path)
parser.add_argument('--target', help='Build target triple')
parser.add_argument('--cc', default='cc')
parser.add_argument('--ld', default='ld')
parser.add_argument('--ar', default='ar')
parser.add_argument('--strip', default='strip')
parser.add_argument('--output', type=Path)
args = parser.parse_args()
main(args)
