**_This is a fork of an [updated version](https://github.com/vamegh/pakrat) of the pakrat libraries by [Vamegh Hedayati](https://github.com/vamegh), forked from the [original](https://github.com/ryanuber/pakrat) by [Ryan Uber](https://github.com/ryanuber). It is not backwards-compatible._**

Yumsync
-------

Yumsync is a tool used to mirror yum repositories and optionally version the repository metadata. This will enable the ability of taking frequent snapshots of a repository without worrying about wasted space from duplicate packages.

What this supports
-------------------

* Mirroring remote repositories
* Creating local repositories (from local packages)
* User-defined folder structure for public access through Nginx or equivalent
* Ability to create versioned snapshots of repository metadata
* Stable and latest links for versioned snapshots
* Symbolic or hard linking for versioned snapshots
* Hard linking allows files to be deleted without affecting other versioned snapshots
* Friendly visual output provided by [blessings](https://pypi.python.org/pypi/blessings) when running under a TTY
* Logs of sync activity are stored alongside the the repository metadata - this provides easy reporting and troubleshooting

Recommended Usage (Docker)
--------------------------

There is a companion Docker image that makes using Yumsync very simple. It can be found under the namespace [jrwesolo/yumsync](https://hub.docker.com/r/jrwesolo/yumsync/) on the [Docker Registry](https://hub.docker.com). It's corresponding GitHub repository can be found [here](https://github.com/jrwesolo/docker_yumsync). The [README.md](https://github.com/jrwesolo/docker_yumsync/blob/master/README.md) has detailed instructions on its usage. There is also a step-by-step walkthrough under the ["Full Example with Nginx"](https://github.com/jrwesolo/docker_yumsync/blob/master/README.md#full-example-with-nginx) section.

Other Usage Types
-----------------

Yumsync can also be used in two other ways. The easiest would be the CLI tool `yumsync`. The second would be by building your own tool and using the Yumsync libraries. If the second method is more your style, please use the [Yumsync CLI](bin/yumsync) as a guide.

CLI Usage
---------

The CLI tool us called `yumsync`. This tool will provide the functionality for most users.

```
usage: yumsync [-h] [-o DIRECTORY] -c CONFIG [-n NAME] [-s]

Sync YUM repositories with optional versioned snapshots.

optional arguments:
  -h, --help            show this help message and exit
  -o DIRECTORY, --directory DIRECTORY
                        Path to output directory to store repositories,
                        defaults to current directory
  -c CONFIG, --config CONFIG
                        Path to YAML config file describing repositories
  -n NAME, --name NAME  Name (regex supported) of YUM repository (repeatable) from config file
                        to sync instead of all available
  -s, --show            Only show what repositories would be synced
  -v, --version         Show version
  --stable              Only set stable links for YUM repositories
```

The repository configuration is read from a yaml config file. Below is a minimal example of what a config file should look like:

```yaml
---
centos/6/os/x86_64:
    mirrorlist: 'http://mirrorlist.centos.org/?release=6&repo=os&arch=x86_64'
    gpgkey: 'http://mirror.centos.org/centos/6/os/x86_64/RPM-GPG-KEY-CentOS-6'
centos/6/extras/x86_64:
    mirrorlist: 'http://mirrorlist.centos.org/?release=6&repo=extras&arch=x86_64'
    gpgkey: 'http://mirror.centos.org/centos/6/os/x86_64/RPM-GPG-KEY-CentOS-6'
centos/6/updates/x86_64:
    mirrorlist: 'http://mirrorlist.centos.org/?release=6&repo=updates&arch=x86_64'
    gpgkey: 'http://mirror.centos.org/centos/6/os/x86_64/RPM-GPG-KEY-CentOS-6'
```

All available options per repo hash:

Option | Type | Default  | Description
------ | ---- | -------- | -----------
`baseurl` | `string`, `array` | `none` | One or more baseurls that will be used to retrieve the desired respository.
`checksum` | `string` | `sha256` | What type of checksum to use when generating repo metadata. `sha256` is generally what you want. If the repository will be consumed by a CentOS 5 machine, use `sha1`.
`combined_metadata` | `boolean` | `false` | If using versioned snapshots, also create metadata in the root of the mirrored repository for all available packages.
`delete` | `boolean` | `false` | Whether or not to delete packages that have been synced, but are no longer present in the repository being mirrored (local or remote). When using `link_type` of `symlink`, packages won't be deleted, but will be excluded from metadata.
`excludepkgs` | `string`, `array` | `none` | Packages to be excluded from the repo. This option supports globbing (e.g. `kernel*`).
`gpgkey` | `string`, `array` | `none` | Url (if local, prefix with `file://`) to the GPG key to store along side the mirror.
`includepkgs` | `string`, `array` | `none` | Packages to be included from the repo. This option supports globbing (e.g. `kernel*`). Packages not included with be ignored.
`link_type` | `string` | `symlink` | Type of link used when creating versioned snapshots or when linking to local packages. Valid values are `hardlink` or `symlink`.
`local_dir` | `string` | `none` | Path to a local folder that contains rpms. These rpms will be used to create a local repository. Supports versioned or unversioned, symlinks or hardlinks.
`mirrorlist` | `string` | `none` | Mirrorlist that will be used to retrieve the desired repository.
`stable` | `string` | `none` | If using versioned snapshots, the version that should be symlinked to `stable` in the mirrored repository.
`version` | `string` | `%Y/%m/%d` | String used by `strftime` to format the current date and time. Please refer to [strftime.org](http://strftime.org) for details.

### Local Repositories

Local repositories are designated by the option `local_dir`. The local directory, as well as the packages inside, must be accessible by `yumsync`. `baseurl` and `mirrorlist` are ignored for local repositories. If hard linking is used, ensure that the local packages exist on the same device as the output directory. `yumsync` will throw an error otherwise due to the requirements of hard links.

### Example of Directory Structure

Output directory is `/data` for these examples. Directory tree is truncated to minimize verbosity.

```bash
# versioned, symlink
/data
├── centos_6_extras_x86_64
│   ├── 2016
│   │   └── 01
│   │       └── 19
│   │           ├── packages -> ../../../packages
│   │           ├── repodata
│   │           └── sync.log
│   ├── RPM-GPG-KEY-CentOS-6
│   ├── latest -> 2016/01/19
│   └── packages
└── public
    └── centos
        └── 6
            └── extras
                └── x86_64 -> ../../../../centos_6_extras_x86_64
```

```bash
# versioned, hardlink
/data
├── centos_6_extras_x86_64
│   ├── 2016
│   │   └── 01
│   │       └── 19
│   │           ├── packages # files inside are hardlinked
│   │           ├── repodata
│   │           └── sync.log
│   ├── RPM-GPG-KEY-CentOS-6
│   ├── latest -> 2016/01/19
│   └── packages
└── public
    └── centos
        └── 6
            └── extras
                └── x86_64 -> ../../../../centos_6_extras_x86_64
```

```bash
# versioned, symlink, combined metadata
/data
├── centos_6_extras_x86_64
│   ├── 2016
│   │   └── 01
│   │       └── 19
│   │           ├── packages -> ../../../packages
│   │           ├── repodata
│   │           └── sync.log
│   ├── RPM-GPG-KEY-CentOS-6
│   ├── latest -> 2016/01/19
│   ├── packages
│   └── repodata
└── public
    └── centos
        └── 6
            └── extras
                └── x86_64 -> ../../../../centos_6_extras_x86_64
```

```bash
# unversioned
/data
├── centos_6_extras_x86_64
│   ├── RPM-GPG-KEY-CentOS-6
│   ├── packages
│   ├── repodata
│   └── sync.log
└── public
    └── centos
        └── 6
            └── extras
                └── x86_64 -> ../../../../centos_6_extras_x86_64
```
