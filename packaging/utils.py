import os
import shutil
from os import PathLike
from os.path import join
from fnmatch import fnmatch
from glob import glob
from pathlib import Path
from typing import List, Tuple, Union, Iterator

# Apply transforms to an iterator.  A transform must be eiather a callable or a tuple (callable, arg1, arg2, ...)
def compose(it, *transforms):
    for transform in transforms:
        if type(transform) is tuple:
            fn, *args = transform
            it = fn(it, *args)
        else:
            it = transform(it)
    return it

PathDuples = Iterator[Tuple[PathLike, PathLike]]

def rel_glob(basedir: PathLike, patterns: Union[str, List[str]]) -> PathDuples:
    if type(patterns) is str:
        patterns = [patterns]
    return iter([(Path(abspath), Path(os.path.relpath(abspath, basedir)))
                for pattern in patterns 
                for abspath in glob(join(basedir, pattern), recursive=True)])

def exclude(files: PathDuples, excludes: List[str]) -> PathDuples:
    for abspath, relpath in files:
        if not any([fnmatch(str(relpath), exclude) for exclude in excludes]):
            yield abspath, relpath

def rel_prefix(files: PathDuples, prefix: PathLike) -> PathDuples:
    for abspath, relpath in files:
        yield abspath, Path(join(prefix, relpath))

def add_to_zip(files: PathDuples, zipfile):
    if zipfile is None:
        return
    for abspath, relpath in files:
        #print('Adding ', relpath)
        zipfile.write(abspath, relpath)

def copy_to(files: PathDuples, target: PathLike):
    for abspath, relpath in files:
        file_target = Path(target) / relpath
        os.makedirs(os.path.dirname(file_target), exist_ok=True)
        shutil.copy(abspath, Path(target) / relpath)

def inspect(files: PathDuples) -> PathDuples:
    for abspath, relpath in files:
        print('###', abspath, relpath)
        yield abspath, relpath
