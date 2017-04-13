import os
from setuptools import setup
from distutils.util import convert_path

main_metadata = {}
metadata_path = convert_path('yumsync/metadata.py')
with open(metadata_path) as metadata_file:
    exec(metadata_file.read(), main_metadata)

setup(
    name='yumsync',
    version=main_metadata['__version__'],
    description='A tool for mirroring and versioning YUM repositories',
    author='Ryan Uber, Vamegh Hedayati, Jordan Wesolowski',
    author_email='ru@ryanuber.com, repo@ev9.io, jrwesolo@gmail.com',
    url='https://github.com/jrwesolo/yumsync',
    packages=['yumsync'],
    scripts=['bin/yumsync'],
    package_data={'yumsync': ['CHANGELOG.md', 'COPYING', 'README.md',]},
    install_requires=['blessings', 'PyYAML', 'pyliblzma'],
    zip_safe=False
)
