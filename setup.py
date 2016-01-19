import sys
from setuptools import setup

def required_module(module):
  """ Test for the presence of a given module.

  This function attempts to load a module, and if it fails to load, a message
  is displayed and installation is aborted. This is required because YUM and
  createrepo are not compatible with setuptools, and yumsync cannot function
  without either one of them.
  """
  try:
    __import__(module)
    return True
  except:
    print '\n'.join([
        'The "%s" module is required, but was not found.' % module,
        'Please install the module and try again.'
    ])
    sys.exit(1)

required_module('yum')
required_module('createrepo')
#required_module('python-blessings')
#required_module('PyYAML')
#required_module('pyliblzma')

setup(name='yumsync',
    version='0.1.0',
    description='A tool for mirroring and versioning YUM repositories',
    author='Ryan Uber, Vamegh Hedayati, Jordan Wesolowski',
    author_email='ru@ryanuber.com, repo@ev9.io, jrwesolo@gmail.com',
    url='https://github.com/jrwesolo/yumsync',
    packages=['yumsync'],
    scripts=['bin/yumsync'],
    package_data={'yumsync': ['LICENSE', 'README.md']}
)
