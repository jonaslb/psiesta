from contextlib import contextmanager
import os
from pathlib import Path


@contextmanager
def chdir(dir):
    old_dir = Path.cwd()
    os.chdir(dir)
    try:
        yield
    finally:
        os.chdir(old_dir)
