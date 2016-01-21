import os
import sys
import tempfile
import shutil
import yum
import createrepo
import copy
from contextlib import contextmanager
from yumsync import util

def factory(name, islocal=False, baseurls=None, mirrorlist=None):
    """ Generate a yumsync.yumbase.YumBase object on-the-fly.

    This makes it possible to mirror YUM repositories without having any stored
    configuration anywhere. Simply pass in the name of the repository, and
    either one or more baseurl's or a mirrorlist URL, and you will get an
    object in return that you can pass to a mirroring function.
    """
    yb = util.get_yum()
    if baseurls is not None:
        util.validate_baseurls(baseurls)
        repo = yb.add_enable_repo(name, baseurls=baseurls)
    elif mirrorlist is not None:
        util.validate_mirrorlist(mirrorlist)
        repo = yb.add_enable_repo(name, mirrorlist=mirrorlist)
    elif islocal:
        repo = yb.add_enable_repo(name)
    else:
        raise Exception('One or more baseurls or mirrorlist required')
    return repo

def set_path(repo, path):
    """ Set the local filesystem path to use for a repository object. """
    util.validate_repo(repo)
    result = copy.copy(repo)  # make a copy so the original is untouched

    # The following is wrapped in a try-except to suppress an anticipated
    # exception from YUM's yumRepo.py, line 530 and 557.
    try: result.pkgdir = path
    except yum.Errors.RepoError: pass

    return result

def create_metadata(repo, packages=None, comps=None, checksum=None):
    """ Generate YUM metadata for a repository.

    This method accepts a repository object and, based on its configuration,
    generates YUM metadata for it using the createrepo sister library.
    """

    if "sha" == checksum or "sha1" == checksum:
      sumtype = "sha"
    else:
      sumtype = "sha256"

    util.validate_repo(repo)
    conf = createrepo.MetaDataConfig()
    conf.directory = os.path.dirname(repo.pkgdir)
    conf.outputdir = os.path.dirname(repo.pkgdir)
    conf.sumtype = sumtype
    if packages:
        conf.pkglist = packages
    conf.quiet = True

    if comps:
        groupdir = tempfile.mkdtemp()
        conf.groupfile = os.path.join(groupdir, 'groups.xml')
        with open(conf.groupfile, 'w') as f:
            f.write(comps)

    generator = createrepo.SplitMetaDataGenerator(conf)
    generator.doPkgMetadata()
    generator.doRepoMetadata()
    generator.doFinalMove()

    if comps and os.path.exists(groupdir):
        shutil.rmtree(groupdir)

def retrieve_group_comps(repo):
    """ Retrieve group comps XML data from a remote repository.

    This data can be used while running createrepo to provide package groups
    data that clients can use while installing software.
    """
    if repo.enablegroups:
        try:
            yb = util.get_yum()
            yb.repos.add(repo)
            comps = yb._getGroups().xml()
            return comps
        except yum.Errors.GroupsError:
            return None

def localsync(repo, dest, local_dir, checksum, version, stable, link_type, delete, combine=False,
              repocallback=None):

    package_dir = os.path.join(dest, 'packages')

    if "symlink" == link_type:
        util.symlink(package_dir, local_dir)
    else:
        util.make_dir(package_dir)

    version_dir = None

    if version:
        version_dir = os.path.join(dest, version, 'packages')
        if "symlink" == link_type:
            util.symlink(version_dir, os.path.relpath(package_dir, os.path.dirname(version_dir)))
        else:
            util.make_dir(version_dir)

    try:
        repo = set_path(repo, package_dir)
        local_packages = []
        for _fname in os.listdir(local_dir):
            if os.path.isfile(os.path.join(local_dir, _fname)):
                local_packages.append(_fname)
        callback(repocallback, repo, 'repo_init', len(local_packages))

        for _file in local_packages:
            if "symlink" != link_type:
                util.hardlink(os.path.join(local_dir, _file), os.path.join(package_dir, _file))
            callback(repocallback, repo, 'link_pkg', _file)
    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception, e:
        callback(repocallback, repo, 'repo_error', str(e))
        return False
    callback(repocallback, repo, 'repo_complete')

    if delete:
        for _file in os.listdir(package_dir):
            package_path = os.path.join(package_dir, _file)
            if os.path.isfile(package_path):
                if not _file in local_packages:
                    os.unlink(package_path)
                    callback(repocallback, repo, 'delete_pkg', _file)

    pkglist = []
    for _file in os.listdir(package_dir):
        if os.path.isfile(os.path.join(package_dir, _file)):
            pkglist.append(os.path.join(os.path.basename(repo.pkgdir), _file))
            if version_dir and "hardlink" == link_type:
                source_file = os.path.join(package_dir, _file)
                target_file = os.path.join(version_dir, _file)
                util.hardlink(source_file, target_file)

    callback(repocallback, repo, 'repo_metadata', 'building')

    try:
        if version_dir:
            repo = set_path(repo, version_dir)
        create_metadata(repo, pkglist, None, checksum)
    except Exception, e:
        callback(repocallback, repo, 'repo_error', str(e))
        return False

    if version:
        if combine:
            repo = set_path(repo, package_dir)
            create_metadata(repo, pkglist, None, checksum)
        elif os.path.exists(os.path.join(dest, 'repodata')):
            # At this point the combined metadata is stale, so remove it.
            shutil.rmtree(os.path.join(dest, 'repodata'))

    callback(repocallback, repo, 'repo_metadata', 'complete')

    if version:
        util.symlink(os.path.join(dest, 'latest'), version)
        if stable:
            util.symlink(os.path.join(dest, 'stable'), stable)
        elif os.path.lexists(os.path.join(dest, 'stable')):
            os.unlink(os.path.join(dest, 'stable'))
    else:
        if os.path.lexists(os.path.join(dest, 'latest')):
            os.unlink(os.path.join(dest, 'latest'))
        if os.path.lexists(os.path.join(dest, 'stable')):
            os.unlink(os.path.join(dest, 'stable'))

def sync(repo, dest, checksum, version, stable, link_type, delete, combine=False, yumcallback=None,
         repocallback=None):
    """ Sync repository contents from a remote source.

    Accepts a repository, destination path, and an optional version, and uses
    the YUM client library to download all available packages from the mirror.
    If the delete flag is passed, any packages found on the local filesystem
    which are not present in the remote repository will be deleted.
    """

    @contextmanager
    def suppress():
        """ Suppress stdout within a context.

        This is necessary in this use case because, unfortunately, the YUM
        library will do direct printing to stdout in many error conditions.
        Since we are maintaining a real-time, in-place updating presentation
        of progress, we must suppress this, as we receive exceptions for our
        reporting purposes anyways.
        """
        stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')
        yield
        sys.stdout = stdout

    package_dir = os.path.join(dest, 'packages')
    util.make_dir(package_dir)
    version_dir = None

    if version:
        version_dir = os.path.join(dest, version, 'packages')
        if "symlink" == link_type:
            util.symlink(version_dir, os.path.relpath(package_dir, os.path.dirname(version_dir)))
        else:
            util.make_dir(version_dir)
    try:
        yb = util.get_yum()
        repo = set_path(repo, package_dir)
        if yumcallback:
            repo.setCallback(yumcallback)
        yb.repos.add(repo)
        yb.repos.enableRepo(repo.id)
        with suppress():
            # showdups allows us to get multiple versions of the same package.
            ygh = yb.doPackageLists(showdups=True)

        # reinstall_available = Available packages which are installed.
        packages = ygh.available + ygh.reinstall_available

        # Inform about number of packages total in the repo.
        callback(repocallback, repo, 'repo_init', len(packages))

        # Check if the packages are already downloaded. This is probably a bit
        # expensive, but the alternative is simply not knowing, which is
        # horrible for progress indication.
        for po in packages:
            local = po.localPkg()
            if os.path.exists(local):
                if yb.verifyPkg(local, po, False):
                    callback(repocallback, repo, 'local_pkg_exists', util.get_package_filename(po))

        with suppress():
            yb.downloadPkgs(packages)

    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception, e:
        callback(repocallback, repo, 'repo_error', str(e))
        return False
    callback(repocallback, repo, 'repo_complete')

    if delete:
        package_names = []
        for package in packages:
            package_names.append(util.get_package_filename(package))
        for _file in os.listdir(package_dir):
            if not _file in package_names:
                package_path = os.path.join(package_dir, _file)
                os.unlink(package_path)
                callback(repocallback, repo, 'delete_pkg', _file)

    comps = retrieve_group_comps(repo)  # try group data

    if comps is None:
        callback(repocallback, repo, 'repo_group_data', 'unavailable')
    else:
        callback(repocallback, repo, 'repo_group_data', 'available')

    pkglist = []
    for pkg in packages:
        pkglist.append(os.path.join(os.path.basename(repo.pkgdir), util.get_package_filename(pkg)))
        if version_dir and "hardlink" == link_type:
          source_file = os.path.join(package_dir, util.get_package_filename(pkg))
          target_file = os.path.join(version_dir, util.get_package_filename(pkg))
          util.hardlink(source_file, target_file)

    callback(repocallback, repo, 'repo_metadata', 'building')

    try:
        if version_dir:
            repo = set_path(repo, version_dir)
        create_metadata(repo, pkglist, comps, checksum)
    except Exception, e:
        callback(repocallback, repo, 'repo_error', str(e))
        return False

    if version:
        if combine:
            repo = set_path(repo, package_dir)
            create_metadata(repo, pkglist, comps, checksum)
        elif os.path.exists(os.path.join(dest, 'repodata')):
            # At this point the combined metadata is stale, so remove it.
            shutil.rmtree(os.path.join(dest, 'repodata'))

    callback(repocallback, repo, 'repo_metadata', 'complete')

    if version:
        util.symlink(os.path.join(dest, 'latest'), version)
        if stable:
            util.symlink(os.path.join(dest, 'stable'), stable)
        elif os.path.lexists(os.path.join(dest, 'stable')):
            os.unlink(os.path.join(dest, 'stable'))
    else:
        if os.path.lexists(os.path.join(dest, 'latest')):
            os.unlink(os.path.join(dest, 'latest'))
        if os.path.lexists(os.path.join(dest, 'stable')):
            os.unlink(os.path.join(dest, 'stable'))

def callback(callback_obj, repo, event, data=None):
    """ Abstracts calling class callbacks.

    Since callbacks are optional, a function should check if the callback is
    set or not, and then call it, so we don't repeat this code many times.
    """
    if callback_obj and hasattr(callback_obj, event):
        method = getattr(callback_obj, event)
        if data:
            method(repo.id, data)
        else:
            method(repo.id)
