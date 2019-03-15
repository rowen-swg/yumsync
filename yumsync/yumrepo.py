# standard imports
from contextlib import contextmanager
from urllib2 import urlopen
from urlparse import urlparse
import copy
import os
import bisect
from fnmatch import fnmatch
import shutil
import sys
import tempfile
import time
# third-party imports
import createrepo
import yum
# local imports
from yumsync.yumbase import YumBase
import yumsync.util as util

class MetadataBuildError(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

class PackageDownloadError(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

class YumRepo(object):

    def __init__(self, repoid, base_dir, opts=None):
        # make sure good defaults
        if opts is None:
            opts = {}
        opts = self._set_default_opts(opts)
        self._validate_opts(opts)
        self._validate_type(base_dir, 'base_dir', str)

        # set actual repo object
        self.__repo_obj = self._get_repo_obj(repoid, opts['local_dir'], opts['baseurl'], opts['mirrorlist'])
        self.__repo_obj.includepkgs = opts['includepkgs']
        self.__repo_obj.exclude = opts['excludepkgs']
        self.id = repoid
        self.checksum = opts['checksum']
        self.combine = opts['combined_metadata'] if opts['version'] else None
        self.delete = opts['delete']
        self.gpgkey = opts['gpgkey']
        self.link_type = opts['link_type']
        self.local_dir = opts['local_dir']
        self.stable = opts['stable']
        self.version = time.strftime(opts['version']) if opts['version'] else None
        self.srcpkgs = opts['srcpkgs']
        self.newestonly = opts['newestonly']
        self.labels = opts['labels']

        # root directory for repo and packages
        self.dir = os.path.join(base_dir, self._friendly(self.id))
        self.package_dir = os.path.join(self.dir, 'packages')
        # version directory for repo and packages
        self.version_dir = os.path.join(self.dir, self.version) if self.version else None
        self.version_package_dir = os.path.join(self.version_dir, 'packages') if self.version_dir else None
        # log directory for repo
        self.log_dir = self.version_dir if self.version_dir else self.dir
        # public directroy for repo
        self.public_dir = os.path.join(base_dir, 'public', self._sanitize(self.id))

        # set default callbacks
        self.__repo_callback_obj = None
        self.__yum_callback_obj = None

        # set repo placeholders
        self._packages = []
        self._comps = None

    @staticmethod
    def _validate_type(obj, obj_name, *obj_types):
        valid_types = list(obj_types)
        if obj_name is None:
            obj_name = 'object'
        if len(valid_types) < 1:
            raise ValueError('no valid types were passed in for {}'.format(obj_name))
        if None in obj_types:
            valid_types.remove(None)
            valid_types.sort()
            valid_types.append(type(None))
        if not isinstance(obj, tuple(valid_types)):
            valid_str = ', '.join([t.__name__ for t in valid_types])
            raise TypeError('{} is {}; must be {}'.format(obj_name, type(obj).__name__, valid_str))

    @staticmethod
    def _validate_url(url):
        if not (url.startswith('http://') or url.startswith('https://') or url.startswith('file://')):
            raise ValueError('Unsupported URL format "{}"'.format(url))

    @staticmethod
    def _set_default_opts(opts=None):
        if not isinstance(opts, dict):
            opts = {}
        if 'baseurl' not in opts:
            opts['baseurl'] = None
        if 'checksum' not in opts:
            opts['checksum'] = None
        if 'combined_metadata' not in opts:
            opts['combined_metadata'] = None
        if 'delete' not in opts:
            opts['delete'] = None
        if 'excludepkgs' not in opts:
            opts['excludepkgs'] = None
        if 'gpgkey' not in opts:
            opts['gpgkey'] = None
        if 'includepkgs' not in opts:
            opts['includepkgs'] = None
        if 'link_type' in opts and isinstance(opts['link_type'], str):
            opts['link_type'] = opts['link_type'].lower()
        if 'link_type' not in opts or (opts['link_type'] != 'symlink' and opts['link_type'] != 'hardlink' and opts['link_type'] != 'individual_symlink'):
            opts['link_type'] = 'symlink'
        if 'local_dir' not in opts:
            opts['local_dir'] = None
        if 'mirrorlist' not in opts:
            opts['mirrorlist'] = None
        if 'stable' not in opts:
            opts['stable'] = None
        if not isinstance(opts['stable'], str) and opts['stable'] is not None:
            opts['stable'] = str(opts['stable'])
        if 'version' not in opts:
            opts['version'] = '%Y/%m/%d'
        if 'srcpkgs' not in opts:
            opts['srcpkgs'] = None
        if 'newestonly' not in opts:
            opts['newestonly'] = None
        if 'labels' not in opts:
            opts['labels'] = {}
        return opts

    @classmethod
    def _validate_opts(cls, opts):
        cls._validate_type(opts['baseurl'], 'baseurl', str, list, None)
        if isinstance(opts['baseurl'], list):
            for b in opts['baseurl']:
                cls._validate_type(b, 'baseurl (in list)', str)
                cls._validate_url(b)
        elif isinstance(opts['baseurl'], str):
            cls._validate_url(opts['baseurl'])
        cls._validate_type(opts['checksum'], 'checksum', str, None)
        cls._validate_type(opts['combined_metadata'], 'combined_metadata', bool, None)
        cls._validate_type(opts['delete'], 'delete', bool, None)
        cls._validate_type(opts['excludepkgs'], 'excludepkgs', str, list, None)
        if isinstance(opts['excludepkgs'], list):
            for e in opts['excludepkgs']:
                cls._validate_type(e, 'excludepkgs (in list)', str)
        cls._validate_type(opts['gpgkey'], 'gpgkey', str, list, None)
        if isinstance(opts['gpgkey'], list):
            for g in opts['gpgkey']:
                cls._validate_type(g, 'gpgkey (in list)', str)
                cls._validate_url(g)
        elif opts['gpgkey'] is str:
            cls._validate_url(opts['gpgkey'])
        cls._validate_type(opts['includepkgs'], 'includepkgs', str, list, None)
        if isinstance(opts['includepkgs'], list):
            for i in opts['includepkgs']:
                cls._validate_type(i, 'includepkgs (in list)', str)
        cls._validate_type(opts['link_type'], 'link_type', str)
        cls._validate_type(opts['local_dir'], 'local_dir', str, list, None)
        cls._validate_type(opts['mirrorlist'], 'mirrorlist', str, None)
        if opts['mirrorlist'] is not None:
            cls._validate_url(opts['mirrorlist'])
        cls._validate_type(opts['stable'], 'stable', str, None)
        cls._validate_type(opts['version'], 'version', str, None)
        cls._validate_type(opts['srcpkgs'], 'srcpkgs', bool, None)
        cls._validate_type(opts['newestonly'], 'newestonly', bool, None)
        cls._validate_type(opts['labels'], 'labels', dict)
        for label, value in opts['labels'].iteritems():
            cls._validate_type(label, 'label_name_{}'.format(label), str)
            cls._validate_type(value, 'label_value_{}'.format(label), str)

    @staticmethod
    def _sanitize(text):
        return text.strip().strip('/')

    @classmethod
    def _friendly(cls, text):
        return cls._sanitize(text).replace('/', '_')

    @staticmethod
    def _get_repo_obj(repoid, localdir=None, baseurl=None, mirrorlist=None):
        yb = YumBase()
        if baseurl is not None:
            if isinstance(baseurl, list):
                repo = yb.add_enable_repo(repoid, baseurls=baseurl)
            else:
                repo = yb.add_enable_repo(repoid, baseurls=[baseurl])
        elif mirrorlist is not None:
            repo = yb.add_enable_repo(repoid, mirrorlist=mirrorlist)
        elif localdir:
            repo = yb.add_enable_repo(repoid)
        else:
            raise ValueError('One or more baseurls or mirrorlist required')
        return repo

    def set_repo_callback(self, callback):
        self.__repo_callback_obj = callback

    def set_yum_callback(self, callback):
        self.__yum_callback_obj = callback

    def _set_path(self, path):
        repo = copy.copy(self.__repo_obj)
        try:
            repo.pkgdir = path
        except yum.Errors.RepoError:
            pass
        return repo

    def setup_directories(self):
        if self.local_dir and self.link_type == 'symlink':
            if not os.path.islink(self.package_dir) and os.path.isdir(self.package_dir):
                shutil.rmtree(self.package_dir)

            assert isinstance(self.local_dir, (list, str))
            if isinstance(self.local_dir, list):
                for idx, local_dir in enumerate(self.local_dir):
                    subdir = os.path.join(self.package_dir, "repo_{}".format(idx))
                    util.symlink(subdir, local_dir)
            elif isinstance(self.local_dir, str):
                util.symlink(self.package_dir, self.local_dir)
        else:
            if os.path.islink(self.package_dir):
                os.unlink(self.package_dir)
            util.make_dir(self.package_dir)

        if self.version_dir:
            if os.path.islink(self.version_package_dir) or os.path.isfile(self.version_package_dir):
                os.unlink(self.version_package_dir)
            elif os.path.isdir(self.version_package_dir):
                shutil.rmtree(self.version_package_dir)
            if self.link_type == 'symlink':
                util.symlink(self.version_package_dir, os.path.relpath(self.package_dir, self.version_dir))
            elif self.link_type == 'individual_symlink':
                util.make_dir(self.version_package_dir)
                if isinstance(self.local_dir, list):
                    dirs = self.local_dir
                    single = False
                elif isinstance(self.local_dir, str):
                    dirs = [self.local_dir]
                    single = True
                for idx, _dir in enumerate(dirs):
                    pkg_dir = self.version_package_dir
                    if not single:
                        pkg_dir = os.path.join(self.version_package_dir, "repo_{}".format(idx))
                        util.make_dir(os.path.join(pkg_dir))
                    for _file in self._find_rpms(_dir):
                        util.symlink(os.path.join(pkg_dir, _file), os.path.join(_dir, _file))
            else: # hardlink
                util.make_dir(self.version_package_dir)

    def download_gpgkey(self):
        if self.gpgkey:
            gpgkey_paths = []
            if isinstance(self.gpgkey, list):
                gpgkey_iter = self.gpgkey
            else:
                gpgkey_iter = [self.gpgkey]
            for gpgkey in gpgkey_iter:
                try:
                    keyname = os.path.basename(urlparse(gpgkey).path)
                    key_path = os.path.join(self.dir, keyname)
                    if not os.path.exists(key_path):
                        key_data = urlopen(gpgkey)
                        with open(key_path, 'w') as f:
                            f.write(key_data.read())
                        key_data.close()
                        self._callback('gpgkey_download', os.path.basename(key_path))
                    else:
                        self._callback('gpgkey_exists', os.path.basename(key_path))
                    gpgkey_paths.append(key_path)
                except Exception as e:
                    self._callback('gpgkey_error', str(e))
            return gpgkey_paths
        return None

    def prepare_packages(self):
        self.download_packages()
        self.prune_packages()
        self.version_packages()

    def download_packages(self):
        if self.local_dir:
            self._download_local_packages()
        else:
            self._download_remote_packages()

    def _validate_packages(self, directory, packages):
        ts = yum.rpmUtils.transaction.initReadOnlyTransaction()
        if isinstance(packages, str):
            self._callback('pkg_exists', packages)
            return self._validate_package(ts, directory, packages)
        elif isinstance(packages, list):
            valid = []
            for pkg in packages:
                if self._validate_package(ts, directory, pkg):
                    valid.append(pkg)
                    self._callback('pkg_exists', pkg)
            return valid
        else:
            return None

    @staticmethod
    def _validate_package(ts, directory, package):
        h = None

        try:
            pkg_path = os.path.join(directory, package)
            h = yum.rpmUtils.miscutils.hdrFromPackage(ts, pkg_path)
        except yum.rpmUtils.RpmUtilsError:
            pass
        return h

    def _find_rpms(self, local_dir):
        matches = []
        progress_counter = 0
        include_globs = []
        exclude_globs = []
        if self.__repo_obj.includepkgs is not None:
            if isinstance(self.__repo_obj.includepkgs, list):
                include_globs = self.__repo_obj.includepkgs
            elif isinstance(self.__repo_obj.includepkgs, str):
                include_globs = [self.__repo_obj.includepkgs]
        if self.__repo_obj.exclude is not None:
            if isinstance(self.__repo_obj.exclude, list):
                exclude_globs = self.__repo_obj.exclude
            elif isinstance(self.__repo_obj.exclude, str):
                exclude_globs = [self.__repo_obj.exclude]

        for root, dirnames, filenames in os.walk(local_dir, topdown=False, followlinks=True):
            for filename in filenames:
                if not filename.endswith('.rpm'):
                    continue
                skip = False
                keep = True
                for glob in exclude_globs:
                    if fnmatch(filename, glob):
                        skip = True
                        break
                if skip:
                    continue
                for glob in include_globs:
                    if fnmatch(filename, glob):
                        keep = True
                        break
                    else:
                        keep = False
                if not keep:
                    continue
                bisect.insort(matches, os.path.relpath(os.path.join(root, filename), local_dir))

        return matches

    def _download_local_packages(self):
        try:
            packages = {}
            nb_packages = 0
            self._callback('repo_init', nb_packages, True)
            if isinstance(self.local_dir, str):
                files = self._find_rpms(self.local_dir)
                packages = {(None, self.local_dir): self._validate_packages(self.local_dir, files)}
                nb_packages += len(packages[(None, self.local_dir)])
            elif isinstance(self.local_dir, list):
                packages = {}
                for idx, local_dir in enumerate(self.local_dir):
                    files = self._find_rpms(local_dir)
                    nb_packages += len(files)
                    self._callback('repo_init', nb_packages, True)
                    packages[(idx, local_dir)] = self._validate_packages(local_dir, files)
            self._callback('repo_init', nb_packages, True)


            for _dir, _files in packages.iteritems():
                for _file in _files:
                    if _dir[0] is not None and isinstance(_dir[0], int):
                        package_dir = os.path.join(self.package_dir, "repo_{}".format(_dir[0]))
                        file_path = os.path.join("repo_{}".format(_dir[0]), _file)
                    else:
                        package_dir = self.package_dir
                        file_path = _file
                    self._packages.append(file_path)
                    if self.link_type == 'hardlink':
                        status = util.hardlink(os.path.join(_dir[1], _file), os.path.join(package_dir, _file))
                        if status:
                            size = os.path.getsize(os.path.join(_dir[1], _file))
                            self._callback('link_local_pkg', _file, size)

            self._callback('repo_complete')
        except (KeyboardInterrupt, SystemExit):
            pass
        except Exception as e:
            self._callback('repo_error', str(e))
            raise PackageDownloadError(str(e))

    def _download_remote_packages(self):
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

        try:
            yb = YumBase()
            if self.srcpkgs:
                if not 'src' in yb.arch.archlist:
                    yb.arch.archlist.append('src')
            repo = self._set_path(self.package_dir)
            if self.__yum_callback_obj:
                repo.setCallback(self.__yum_callback_obj)
            yb.repos.add(repo)
            yb.repos.enableRepo(repo.id)
            with suppress():
                if self.newestonly:
                  packages = yb.pkgSack.returnNewestByNameArch()
                else:
                  packages = yb.pkgSack.returnPackages()
            # Inform about number of packages total in the repo.
            self._callback('repo_init', len(packages))
            # Check if the packages are already downloaded. This is probably a bit
            # expensive, but the alternative is simply not knowing, which is
            # horrible for progress indication.
            for po in packages:
                local = po.localPkg()
                self._packages.append(os.path.basename(local))
                if os.path.exists(local):
                    if yb.verifyPkg(local, po, False):
                        self._callback('pkg_exists', os.path.basename(local))
            with suppress():
                yb.downloadPkgs(packages)

            self._callback('repo_complete')
        except (KeyboardInterrupt, SystemExit):
            pass
        except Exception as e:
            self._callback('repo_error', str(e))
            raise PackageDownloadError(str(e))

    def prune_packages(self):
        # exit if we don't have packages
        if not self._packages or len(self._packages) == 0:
            return
        if self.delete:
            if not self.version or (self.link_type != 'symlink' and self.link_type != 'individual_symlink'):
                for _file in os.listdir(self.package_dir):
                    if _file not in self._packages:
                        os.unlink(os.path.join(self.package_dir, _file))
                        self._callback('delete_pkg', _file)
        else:
            packages_to_validate = sorted(list(set(os.listdir(self.package_dir)) - set(self._packages)))
            self._packages.extend(self._validate_packages(self.package_dir, packages_to_validate))

    def version_packages(self):
        # exit if we don't have packages
        if not self._packages or len(self._packages) == 0:
            return
        if self.version and self.link_type == 'hardlink':
            for pkg in self._packages:
                source_file = os.path.join(self.package_dir, pkg)
                target_file = os.path.join(self.version_package_dir, pkg)
                util.hardlink(source_file, target_file)

    def get_group_data(self):
        if self.local_dir:
            self._comps = None
        else:
            try:
                yb = YumBase()
                yb.repos.add(self.__repo_obj)
                self._comps = yb._getGroups().xml()
            except yum.Errors.GroupsError:
                pass
        if self._comps:
            self._callback('repo_group_data', 'available')
        else:
            self._callback('repo_group_data', 'unavailable')

    def build_metadata(self):
        staging = tempfile.mkdtemp(prefix='yumsync-', suffix='-metadata')

        if self.checksum == 'sha' or self.checksum == 'sha1':
            sumtype = 'sha'
        else:
            sumtype = 'sha256'

        conf = createrepo.MetaDataConfig()
        conf.directory = os.path.dirname(self.package_dir)
        conf.outputdir = staging
        conf.sumtype = sumtype
        conf.workers = 4
        conf.pkglist = ["packages/{}".format(pkg) for pkg in self._packages]

        conf.quiet = True

        if self._comps:
            groupdir = tempfile.mkdtemp(prefix='yumsync-', suffix='-groupdata')
            conf.groupfile = os.path.join(groupdir, 'groups.xml')
            with open(conf.groupfile, 'w') as f:
                f.write(self._comps)

        generator = createrepo.SplitMetaDataGenerator(conf)

        if conf.pkglist != []:
            generator.doPkgMetadata()
            generator.doRepoMetadata()
            generator.doFinalMove()

        if self._comps and os.path.exists(groupdir):
            shutil.rmtree(groupdir)

        return staging

    def build_file_list(self):
        if os.path.exists(os.path.join(self.log_dir, 'filelist')):
            os.unlink(os.path.join(self.log_dir, 'filelist'))
        with open(os.path.join(self.log_dir, 'filelist'), 'w') as f:
            for pkg in self._packages:
                f.write('packages/{}\n'.format(pkg))


    def prepare_metadata(self):
        self.get_group_data()
        self._callback('repo_metadata', 'building')

        try:
            self.build_file_list()
            staging = self.build_metadata()
        except Exception as e:
            self._callback('repo_error', str(e))
            raise MetadataBuildError(str(e))

        repodata_dir = os.path.join(self.dir, 'repodata')
        if os.path.exists(repodata_dir):
            shutil.rmtree(repodata_dir)
        if not self.version or self.combine:
            shutil.copytree(os.path.join(staging, 'repodata'), repodata_dir)

        if self.version:
            repodata_dir = os.path.join(self.version_dir, 'repodata')
            if os.path.exists(repodata_dir):
                shutil.rmtree(repodata_dir)
            shutil.copytree(os.path.join(staging, 'repodata'), repodata_dir)

        # cleanup temporary metadata
        shutil.rmtree(staging)

        self._callback('repo_metadata', 'complete')

    def create_links(self):
        if self.version:
            util.symlink(os.path.join(self.dir, 'latest'), self.version)
            self._callback('repo_link_set', 'latest', self.version)
            if self.stable:
                util.symlink(os.path.join(self.dir, 'stable'), self.stable)
                self._callback('repo_link_set', 'stable', self.stable)
            elif os.path.lexists(os.path.join(self.dir, 'stable')):
                os.unlink(os.path.join(self.dir, 'stable'))
            for label, version in self.labels.iteritems():
                util.symlink(os.path.join(self.dir, label), version)
                self._callback('repo_link_set', label, version)

        else:
            if os.path.lexists(os.path.join(self.dir, 'latest')):
                os.unlink(os.path.join(self.dir, 'latest'))
            if os.path.lexists(os.path.join(self.dir, 'stable')):
                os.unlink(os.path.join(self.dir, 'stable'))

    def sync(self):
        try:
            self.setup_directories()
            self.download_gpgkey()
            self.prepare_packages()
            self.prepare_metadata()
            self.create_links()
        except MetadataBuildError:
            return False
        except PackageDownloadError:
            return False

    def __str__(self):
        raw_info = {}
        if self.checksum:
            raw_info['checksum'] = self.checksum
        if self.combine is not None:
            raw_info['combine'] = self.combine
        if self.delete is not None:
            raw_info['delete'] = self.delete
        if self.gpgkey:
            raw_info['gpgkey'] = self.gpgkey
        if self.link_type:
            raw_info['link_type'] = self.link_type
        if self.local_dir:
            raw_info['local_dir'] = str(self.local_dir)
        if self.stable:
            raw_info['stable'] = self.stable
        if self.version:
            raw_info['version'] = self.version
        if self.srcpkgs is not None:
            raw_info['srcpkgs'] = self.srcpkgs
        if self.newestonly is not None:
            raw_info['newestonly'] = self.newestonly
        if self.labels is not []:
            raw_info['labels'] = str(self.labels)
        friendly_info = ['{}({})'.format(k, raw_info[k]) for k in sorted(raw_info)]
        return '{}: {}'.format(self.id, ', '.join(friendly_info))

    def _callback(self, event, *args):
        if self.__repo_callback_obj and hasattr(self.__repo_callback_obj, event):
            method = getattr(self.__repo_callback_obj, event)
            method(self.id, *args)
