import json
import os
from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))

def read_version(*file_paths):
    path = os.path.join(here, *file_paths)
    with open(path) as metadata_file:
        metadata = json.load(metadata_file)
    if 'version' in metadata:
        return metadata['version']
    else:
        raise RuntimeError("Unable to find version in {0}".format(path))

setup(
    name='yumsync',
    version=read_version('metadata.json'),
    description='A tool for mirroring and versioning YUM repositories',
    author='Ryan Uber, Vamegh Hedayati, Jordan Wesolowski',
    author_email='ru@ryanuber.com, repo@ev9.io, jrwesolo@gmail.com',
    url='https://github.com/jrwesolo/yumsync',
    packages=['yumsync'],
    scripts=['bin/yumsync'],
    package_data={'yumsync': ['LICENSE', 'README.md']},
    data_files=[('', ['metadata.json'])],
    install_requires=['blessings', 'PyYAML', 'pyliblzma'],
    zip_safe=False
)
