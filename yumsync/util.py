# yumsync - A tool for mirroring and versioning YUM repositories.
# Copyright 2013 Ryan Uber <ru@ryanuber.com>. All rights reserved.
#
# MIT LICENSE
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import os
import yum
from yumsync.yumbase import YumBase

def friendly(name):
    return sanitize(name).replace('/', '_')

def sanitize(name):
    return name.strip().strip('/')

def get_yum():
    """ Retrieve a YumBase object, pre-configured. """
    return YumBase()

def get_repo_dir(base_dir, name):
    """ Return the path to a repository directory.

    This is the directory in which all of the repository data will live. The
    path can be relative or fully qualified.
    """
    return os.path.join(base_dir, name)

def get_package_filename(pkg):
    """ From a repository object, return the name of the RPM file. """
    return '%s-%s-%s.%s.rpm' % (pkg.name, pkg.version, pkg.release, pkg.arch)

def validate_type(obj, obj_name, obj_type):
    if type(obj) is not obj_type:
        raise Exception('%s must be %s, not %s' % (obj_name, obj_type, type(obj)))

def validate_base_dir(base_dir):
    """ Validate the input of a base_dir.

    Since a base_dir can be either absolute or relative, the only thing we can
    really validate here is that the value is a regular string.
    """
    validate_type(base_dir, 'base_dir', str)

def validate_url(url):
    """ Validate a source URL. http(s) or file-based accepted. """
    if not (url.startswith('http://') or url.startswith('https://') or
            url.startswith('file://')):
        raise Exception('Unsupported URL format "%s"' % url)

def validate_baseurl(baseurl):
    """ Validate user input of a repository baseurl. """
    validate_type(baseurl, 'baseurl', str)
    validate_url(baseurl)

def validate_checksums(checksums):
    """ Validate user input of a repository checksum. """
    validate_type(checksums, 'checksums', list)

def validate_stable_vers(stable_vers):
    validate_type(stable_vers, 'stable_ver', list)

def validate_link_types(link_types):
    validate_type(link_types, 'link_types', list)

def validate_repo_vers(repo_vers):
    validate_type(repo_vers, 'repo_vers', list)

def validate_deletes(deletes):
    validate_type(deletes, 'deletes', list)

def validate_combines(combines):
    validate_type(combines, 'combines', list)

def validate_local_dirs(local_dirs):
    validate_type(local_dirs, 'local_dirs', list)

def validate_baseurls(baseurls):
    """ Validate multiple baseurls from a list. """
    validate_type(baseurls, 'baseurl', list)
    for baseurl in baseurls:
        validate_baseurl(baseurl)

def validate_mirrorlist(mirrorlist):
    """ Validate a repository mirrorlist source. """
    validate_type(mirrorlist, 'mirrorlist', str)
    if mirrorlist.startswith('file://'):
        raise Exception('mirrorlist cannot use a file:// source.')
    validate_url(mirrorlist)

def validate_repo(repo):
    """ Validate a repository object. """
    validate_type(repo, 'repo', yum.yumRepo.YumRepository)

def validate_repos(repos):
    """ Validate repository objects. """
    validate_type(repos, 'repos', list)
    for repo in repos:
        validate_repo(repo)

def make_dir(path):
    """ Create a directory recursively, if it does not exist. """
    if not os.path.exists(path):
        os.makedirs(path)

# path = path to symlink
# target = path to real file
def symlink(path, target):
    """ Create a symbolic link.
    Determines if a link in the destination already exists, and if it does,
    updates its target. If the destination exists but is not a link, throws an
    exception. If the link does not exist, it is created.
    """
    if not os.path.islink(path):
        if os.path.exists(path):
            raise Exception('%s exists - Cannot create symlink' % path)
        path_dir = os.path.dirname(path)
        if not os.path.exists(path_dir):
            make_dir(path_dir)
    elif os.readlink(path) != target:
        os.unlink(path)
    if os.path.lexists(path):
        return False
    else:
        os.symlink(target, path)
        return True


def hardlink(source, target):
    " This method creates a hardlink ... "
    if source != target:
        # ensure source exists and collect stats
        if not os.path.exists(source):
            raise Exception('%s does not exist - Cannot create hardlink' % source)
        else:
            source_stat = os.stat(source)
        # create target dir if missing
        target_dir = os.path.dirname(target)
        if not os.path.exists(target_dir):
            make_dir(target_dir)
        # get dev and inode info for target
        if os.path.exists(target):
            target_dev = os.stat(target).st_dev
            target_inode = os.stat(target).st_ino
        else:
            target_dev = os.stat(target_dir).st_dev
            target_inode = None
        if target_dev != source_stat.st_dev:
            raise Exception('source device %s is not equal to target device %s - Cannot create hardlink' %
                            (source_stat.st_dev, target_dev))
        elif (target_inode is not None) and (target_inode != source_stat.st_ino):
            os.unlink(target)

        if os.path.exists(target):
            return False
        else:
            os.link(source, target)
            return True
