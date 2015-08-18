
What this is:
-------------
  * This is an updated version of the pakrat libraries and pakrat cli tool, forked from the original By Ryan Uber.

What this supports:
-------------------
  * Building yum repos for Centos 5
  * More descriptive approach to building repositories.
  * Creating repositories for custom local rpms (local repo creation)
  * Stable and Latest repo paths created -- stable linking to a known good repo date.
  * hard linking / symlinking paths -- this allows to maintain repository state by deleting files as hardlinks maintain deleted files
  * output formatting in colour and handled by the blessings library - real time progress indicator seems to be working properly now.
  * new command line tool called reposync.

What this does not support:
---------------------------
  * The original pakrat command line tool - this has now been replaced with reposync.
  * Combined Repository metadata

Most of the changes made have been to:
--------------------------------------

```
  * pakrat/__init__.py
  * pakrat/repo.py
  * pakrat/util.py
  * bin/reposync (pakrat cli no longer exists)
```

Known Issues:
-------------

There is a lot of room for improvement in the updates applied so far,
centos5 mapping is a bit pants, the repo osver has to be marked as centos5 or 5 for it to use sha hashing.
If you fork from this and make any improvements let me know and I will merge it into this version as well.

Reposync Usage:
------

## Introduction

reposync is a command line tool for synchronising remote yum repositories and creating new local yum repositories.


## Usage

repsync usage is as follows:


``` ./reposync -c ../config/repos.yaml

Usage: reposync [options]

Repositories are read in from a yaml config default is /etc/reposync/repos.yaml
the all or name options should be specified to update repositories
the name option can be repeated several times to update multiple repos
the show option will display all available repo names that can be called.

Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -a, --all             all of the repositories listed in the config file will
                        be updated - either this or the name option must be
                        specified
  -c CONFIG, --config=CONFIG
                        Provide a custom configuration file, defaults to
                        /etc/reposync/repos.yaml if none provided
  -d DIRECTORY, --directory=DIRECTORY
                        Set the base path to store the repositories - default
                        read from config file. This overrides config file
  -n NAME, --name=NAME  The name of a YUM repository as contained within the
                        config (repeatable) either this or the all option must
                        be specified
  -s, --show            Display all available YUM repositories as contained
                        within the config

```

The repositories are read in from repos.yaml

The syntax of repos.yaml is as follows:

```
basepath: "/var/www/html/repos"

repos:
  repo-zabbix7:
    name: "zabbix"
    url: "http://repo.zabbix.com/zabbix/2.2/rhel/7/x86_64"
    arch: "x86_64"
    osver: "centos7"
    stable_release: "20150320"
    link_type: hardlink
    delete: true
  repo-local-test:
    name: "local-test"
    arch: "x86_64"
    osver: "centos6"
    stable_release: "20150325"
    repo_type: "local"
    link_type: symlink
    delete: false
```

The basepath will default to /var/www/html, this value must be set to the base location where all repositories will be managed from.

The repos stanza, then requires a unique identifier, so for example repo-zabbix7 - this name is used to select the repository on a command line run as shown above, it is not used by pakrat or reposync as anything else other than a unique identifier.

* name:
The name field should be set to the name of the repository, this does not need to be unique.

* repo_type:
This must be set to local if the repo_type is a local path that needs to be converted and versioned into a proper functioning yum repository.

* url:
The url should be set if the repository in question is a remote repository.

* arch:
this must be set and indicates the arch of the repo, this is used to determine the repo path and can be x86_64, noarch or i386 (this can be set to anything though)

* osver:
This must be set. For centos5 repos to work and to have the correct hash applied this must be set to centos5 or 5 (currently the check employed is very basic)

* stable_release:
This again must be set and should be set to a valid versioned release, the format is as as follows: YYYYMMDD, all repos are datestamp versioned / archived in this method.

* link_type:
This supports two different link types, either symlink or hardlink, if hardlink is set then rpm files are hardlinked but the latest and stable directories are symlinked -- this allows for repositories to be tracked as they change so as files are deleted remotely they can be tracked locally (hardlinking will keep the file in previous versioned repos while newer versions can have the files deleted)
This defaults to symlink if not specified.

* delete:
This can be either true or false, if not set it defaults to false and if link_type is set to symlink this option is ignored and set to false.
This allows the repo packages to be deleted as packages are deleted on the remote repo. This is only useful for hardlinked repos.

### Local Repositories
The Local method listed above obviously expects the rpms to be available locally, but it also requires the path structure to match the remote method path creation and for the rpms to be available in that path.

Lets say the repos.yaml states:

```
basepath: "/var/www/html/repos"
repos:
  repo-c6-64-local-test:
    name: "local-test"
    arch: "x86_64"
    osver: "centos6"
    stable_release: "22042015"
    repo_type: "local"
```

The path structure is as follows:

```
<base_path>/<name>/<osver>/<arch>/
```

Given the example above, the local method will expect the rpms to be in :

```
/var/www/html/repos/local-test/centos6/x86_64/*.rpm
```

If the path doesnt exist it will create the path structure but cannot create repo data, it will inform you of the path it expects the rpms to be in. Once the rpms are in place reposync can make it into a rpm repository and control it.


### Remote Repositories

For a remote repository, it works the same way, except, it sends it to the following path:

```
  $basepath/$name/$osver/$arch
```

Taking zabbix from the yaml example above, the directory structure would be as follows:

```
/var/www/html/repos/zabbix2.2:

# tree -d
.
├── centos6
│   ├── 20150407
│   │   ├── repodata
│   │   └── x86_64 -> ../x86_64
│   ├── 20150408
│   │   ├── repodata
│   │   └── x86_64 -> ../x86_64
│   ├── 20150413
│   │   ├── repodata
│   │   └── x86_64 -> ../x86_64
│   ├── 20150420
│   │   ├── repodata
│   │   └── x86_64 -> ../x86_64
│   ├── latest -> 20150420
│   ├── stable -> 20150407
│   └── x86_64
└── centos7
    ├── 20150407
    │   ├── repodata
    │   └── x86_64 -> ../x86_64
    ├── 20150408
    │   ├── repodata
    │   └── x86_64 -> ../x86_64
    ├── 20150413
    │   ├── repodata
    │   └── x86_64 -> ../x86_64
    ├── 20150420
    │   ├── repodata
    │   └── x86_64 -> ../x86_64
    ├── latest -> 20150420
    ├── stable -> 20150407
    └── x86_64

```


OLD INSTRUCTIONS (NOT REALLY APPLICABLE NOW)
--------------------------------------------

Pakrat
-------

A tool to mirror and version YUM repositories
The modrepo forked version extends the paths created when versioning and enables a stable link,
so that a latest and stable version can be set for each repo.

What does it do?
----------------

* You invoke pakrat and pass it some information about your repositories.
* Pakrat mirrors the YUM repositories, and optionally arranges the data in a
  versioned manner.

It is easiest to demonstrate what Pakrat does by shell example:
```
$ pakrat --repodir /etc/yum.repos.d

  repo              done/total       complete    metadata
  -------------------------------------------------------
  base               357/6381        5%          -
  updates            112/1100        10%         -
  extras              13/13          100%        complete

  total:             482/7494        6%

```

Features
--------

* Mirror repository packages from remote sources
* Optional repository versioning with user-defined version schema
* Mirror YUM group metadata
* Supports standard YUM configuration files
* Supports YUM configuration directories (repos.d style)
* Supports command-line repos for zero-configuration (`--name` and `--baseurl`)
* Command-line interface with real-time progress indicator
* Parallel repository downloads for maximum effeciency
* Syslog integration
* Supports user-specified callbacks

Installation
------------

Pakrat is available in PyPI as `pakrat`. That means you can install it with
easy_install:

```
# easy_install pakrat
```

*NOTE*
Installation from PyPI should work on any Linux. However, since Pakrat depends
on YUM and Createrepo, which are not available in PyPI, these dependencies will
not be detected as missing. The easiest install path is to install on some kind
of RHEL like so:

```
# yum -y install createrepo
# easy_install pakrat
```

How to use it
-------------

The simplest possible example would involve mirroring a YUM repository in a
very basic way, using the CLI:

```
$ pakrat --name centos --baseurl http://mirror.centos.org/centos/6/os/x86_64
$ tree -d centos
centos/
├── Packages
└── repodata
```

A slightly more complex example would be to version the same repository. To
do this, you must pass in a version number. An easy example is to mirror a
repository daily.
```
$ pakrat \
    --repoversion $(date +%Y-%m-%d) \
    --name centos \
    --baseurl http://mirror.centos.org/centos/6/os/x86_64
$ tree -d centos
centos/
├── 2013-07-29
│   ├── Packages -> ../Packages
│   └── repodata
├── latest -> 2013-07-29
└── Packages
```

If you were to configure the above to command to run on a daily schedule,
eventually you would see something like:
```
$ tree -d centos
centos/
├── 2013-07-29
│   ├── Packages -> ../Packages
│   └── repodata
├── 2013-07-30
│   ├── Packages -> ../Packages
│   └── repodata
├── 2013-07-31
│   ├── Packages -> ../Packages
│   └── repodata
├── latest -> 2013-07-31
└── Packages
```

You can also opt to have a combined repository for each of your repos. This is
useful because you could simply point your clients to the root of your
repository, and they will have access to its complete history of RPMs. You can
do this by passing in the `--combined` option when versioning repositories.

Pakrat is also capable of handling multiple YUM repositories in the same mirror
run. If multiple repositories are specified, each repository will get its own
download thread. This is handy if you are syncing from a mirror that is not
particularly quick. The other repositories do not need to wait on it to finish.
```
$ pakrat \
    --repoversion $(date +%Y-%m-%d) \
    --name centos --baseurl http://mirror.centos.org/centos/6/os/x86_64 \
    --name epel --baseurl http://dl.fedoraproject.org/pub/epel/6/x86_64
$ tree -d centos epel
centos/
├── 2013-07-29
│   ├── Packages -> ../Packages
│   └── repodata
├── latest -> 2013-07-29
└── Packages
epel/
├── 2013-07-29
│   ├── Packages -> ../Packages
│   └── repodata
├── latest -> 2013-07-29
└── Packages
```

Configuration can also be passed in from YUM configuration files. See the CLI
`--help` for details.

Pakrat also exposes its interfaces in plain python for integration with other
projects and software. A good starting point for using Pakrat via the python
API is to take a look at the `pakrat.sync` method. The CLI calls this method
almost exclusively, so it should be fairly straightforward in its usage (all
arguments are named and optional):
```
pakrat.sync(basedir, objrepos, repodirs, repofiles, repoversion, delete, callback)
```

Another handy python method is `pakrat.repo.factory`, which creates YUM
repository objects so that no file-based configuration is needed.
```
pakrat.repo.factory(name, baseurls=None, mirrorlist=None)
```

User-defined callbacks
----------------------

Since the YUM team did a decent job at externalizing the progress data,
pakrat will return the favor by exposing the same data, plus some extras
via user callbacks.

A user callback is a simple class that implements some methods for handling
received data. It is not mandatory to implement any of the methods.

A few of the available user callbacks in pakrat come directly from the
`urlgrabber` interface (namely, any user callback beginning with `download_`.
The other methods are called by pakrat, which explains why the interfaces
are varied.

The supported user callbacks are listed in the following method signatures:
```python
""" Called when the number of packages a repository contains becomes known """
repo_init(repo_id, num_pkgs)

""" Called when 'createrepo' begins running and when it completes """
repo_metadata(repo_id, status)

""" Called when a repository finishes downloading all packages """
repo_complete(repo_id)

""" Called whenever an exception is thrown from a repo thread """
repo_error(repo_id, error)

""" Called when a package becomes known as 'already downloaded' """
local_pkg_exists(repo_id, pkgname)

""" Called when a file begins downloading (non-exclusive) """
download_start(repo_id, fpath, url, fname, fsize, text)

""" Called during downloads, 'size' is bytes downloaded """
download_update(repo_id, size)

""" Called when a file download completes, 'size' is file size in bytes """
download_end(repo_id, size)
```

The following is a basic example of how to use user callbacks in pakrat.
Note that an instance of the class is passed into the `pakrat.sync()` call
as the named argument `callback`.

```python
import pakrat

class mycallback(object):
    def log(self, msg):
        with open('log.txt', 'a') as logfile:
            logfile.write('%s\n' % msg)

    def repo_init(self, repo_id, num_pkgs):
        self.log('Found %d packages in repo %s' % (num_pkgs, repo_id))

    def download_start(self, repo_id, _file, url, basename, size, text):
        self.fname = basename

    def download_end(self, repo_id, size):
        if self.fname.endswith('.rpm'):
            self.log('%s, repo %s, size %d' % (self.fname, repo_id, size))

    def repo_metadata(self, repo_id, status):
        self.log('Metadata for repo %s is now %s' % (repo_id, status))

myrepo = pakrat.repo.factory(
    'extras',
    mirrorlist='http://mirrorlist.centos.org/?repo=extras&release=6&arch=x86_64'
)

mycallback_instance = mycallback()
pakrat.sync(objrepos=[myrepo], callback=mycallback_instance)
```

If you run the above example, and then take a look in the `log.txt` file (which
the user callbacks should have created), you will see something like:

```
Found 13 packages in repo extras
bakefile-0.2.8-3.el6.centos.x86_64.rpm, repo extras, size 256356
centos-release-cr-6-0.el6.centos.x86_64.rpm, repo extras, size 3996
centos-release-xen-6-2.el6.centos.x86_64.rpm, repo extras, size 4086
freenx-0.7.3-9.4.el6.centos.x86_64.rpm, repo extras, size 99256
jfsutils-1.1.13-9.el6.x86_64.rpm, repo extras, size 244104
nx-3.5.0-2.1.el6.centos.x86_64.rpm, repo extras, size 2807864
opennx-0.16-724.el6.centos.1.x86_64.rpm, repo extras, size 1244240
python-empy-3.3-5.el6.centos.noarch.rpm, repo extras, size 104632
wxBase-2.8.12-1.el6.centos.x86_64.rpm, repo extras, size 586068
wxGTK-2.8.12-1.el6.centos.x86_64.rpm, repo extras, size 3081804
wxGTK-devel-2.8.12-1.el6.centos.x86_64.rpm, repo extras, size 1005036
wxGTK-gl-2.8.12-1.el6.centos.x86_64.rpm, repo extras, size 31824
wxGTK-media-2.8.12-1.el6.centos.x86_64.rpm, repo extras, size 38644
Metadata for repo extras is now working
Metadata for repo extras is now complete
```

Building an RPM
---------------

Pakrat can be easily packaged into an RPM.

1. Download a release and name the tarball `pakrat.tar.gz`:
```
curl -o pakrat.tar.gz -L https://github.com/ryanuber/pakrat/archive/master.tar.gz
```

2. Build it into an RPM:
```
rpmbuild -tb pakrat.tar.gz
```

What's missing
--------------

* Unit tests (preliminary work done in unit_test branch)

Thanks
------

Thanks to [Keith Chambers](https://github.com/keithchambers) for help with the
ideas and useful input on CLI design.
