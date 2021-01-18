#!/usr/bin/env python3
import argparse
from pathlib import Path
from subprocess import check_call

parser = argparse.ArgumentParser()
parser.add_argument('--arch')
parser.add_argument('--build-dir', type=Path)
parser.add_argument('--build-tools', type=Path)
args = parser.parse_args()

project_root = Path(__file__).resolve().parent
build_suffix = '-' + args.arch if args.arch is not None else ''
if args.build_dir:
    build_dir = args.build_dir
elif args.arch:
    build_dir = project_root / ('build-' + args.arch)
else:
    build_dir = project_root / 'build'
build_tools = args.build_tools or project_root.parent / 'build-tools' / 'linux'

check_call(['docker', 'run', '-it',  '--privileged',
            '-v' f'{project_root}:/workspace/source:ro',
            '-v' f'{build_dir}:/workspace/build:rw',
            '-v' f'{build_tools}:/workspace/build-tools:ro',
            '-e' 'BUILD_SOURCESDIRECTORY=/workspace/source',
            '-e' 'AGENT_BUILDDIRECTORY=/workspace/build',
            '-e' 'CMAKE_BUILD_TYPE=RelWithDebInfo',
            '-e' 'SCCACHE_DIR=/workspace/build/.sccache',
            '-e' 'SCCACHE_IDLE_TIMEOUT=60',
            '-w' '/workspace/build',
            '-u' '1000:1000',
            '-v' '/etc/passwd:/etc/passwd',
            'vadimcn/linux-builder:latest',
            'bash', '-c', 'export PATH=/workspace/build-tools/bin:$PATH; bash'])
