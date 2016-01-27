import codecs
import os
import re
import sys
from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))

def read(*parts):
    return codecs.open(os.path.join(here, *parts), 'r').read()

def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")

setup(
    name='yumsync',
    version=find_version('yumsync', '__init__.py'),
    description='A tool for mirroring and versioning YUM repositories',
    author='Ryan Uber, Vamegh Hedayati, Jordan Wesolowski',
    author_email='ru@ryanuber.com, repo@ev9.io, jrwesolo@gmail.com',
    url='https://github.com/jrwesolo/yumsync',
    packages=['yumsync'],
    scripts=['bin/yumsync'],
    package_data={'yumsync': ['LICENSE', 'README.md']},
    install_requires=['blessings', 'PyYAML', 'pyliblzma']
)
