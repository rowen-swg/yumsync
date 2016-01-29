Yumsync CHANGELOG
=================

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
