Yumsync CHANGELOG
=================

v1.1.1 (2017-04-13)
-------------------

* Cleanup packaging
* Use metadata.py instead of metadata.json for versioning

v1.1.0 (2017-02-08)
-------------------

### Feature

* Add support for `includepkgs` and `excludepkgs` for repo configuration
* Allow multiple GPG keys per repo
* Version number is now stored in `metadata.json`

v1.0.0 (2016-09-28)
-------------------

This release is a major refactor of yumsync. It's goal was to simplify the code and reduce unnecessary repetition.

### Feature

* Support setting stable links without resyncing (!)
* Log messages when stable and latest links are set
* More informative logging for local repos
* More intelligent logging for skipped packages
* Only generate metadata once and copy for versioned and combined

### Bugfix

* Handle switching between hardlink and symlink gracefully
* Cover more edge cases when creating directories and symlinks

v0.4.0 (2016-09-15)
-------------------

### Feature

* Add --version flag to display version
* GPG key download happens in each repo's sync thread
* GPG key info is now logged

### Bugfix

* Create links as soon as possible so we don't have to wait for long repos

v0.3.0 (2016-01-29)
-------------------

### Feature

* UI now sorts both by name of repo, but also it's status
* UI uses color to better indicate status of each individual repo

v0.2.1 (2016-01-28)
-------------------

### Bugfix

* Fix incorrect version in `__init__.py`

v0.2.0 (2016-01-28)
-------------------

### Feature

* `--name` now performs matches using regular expressions

### Bugfix

* Running under a TTY and passing `--show` now does not suppress repository list

v0.1.4 (2016-01-27)
-------------------

* Single source for version number
* Remove unneeded function

v0.1.3 (2016-01-26)
-------------------

### Bugfix

* Fix callback function parameters causing `TypeError: start() got an unexpected keyword argument 'filename'`

v0.1.2 (2016-01-21)
-------------------

### Bugfix

* Fix metadata generate for combined metadata (was referencing packages in the versioned directory)

v0.1.1 (2016-01-20)
-------------------

### Bugfix

* Add logic to handle missing config file

v0.1.0 (2016-01-19)
-------------------

* Initial release
