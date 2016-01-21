import os
import sys
import multiprocessing
import signal
import urlparse
from yumsync import util, repo, progress
from yumsync.log import log

__version__ = '0.1.2'

def localsync(repos={}, basedir=None, repoversion=None, link_type=None, callback=None):
  """ Create Repo Metadata from Local package repo
      Also Versions the local repository """
  if not basedir:
    basedir = os.getcwd()  # default current working directory
  util.validate_basedir(basedir)

  for key in repos:
    name = repos[key]["name"]
    dest = util.get_repo_dir(basedir, name)
    delete = repos[key]["delete"]
    osver = repos[key]["osver"]
    arch = repos[key]["arch"]
    stable = repos[key]["stable_release"]
    repo_type = repos[key]["repo_type"]
    url = repos[key]["url"]
    link_type = repos[key]["link_type"]
    repo.localsync(name, dest, osver, arch, repoversion, stable, link_type, delete)

def sync(base_dir=None, obj_repos=[], checksums=[], stable_vers=[],
         link_types=[], repo_vers=[], deletes=[], combines=[],
         local_dirs=[], callback=None):
    """ Mirror repositories with configuration data from multiple sources.

    Handles all input validation and higher-level logic before passing control
    on to threads for doing the actual syncing. One thread is created per
    repository to alleviate the impact of slow mirrors on faster ones.
    """

    if not base_dir:
        base_dir = os.getcwd()  # default current working directory

    util.validate_base_dir(base_dir)
    util.validate_repos(obj_repos)
    util.validate_checksums(checksums)
    util.validate_stable_vers(stable_vers)
    util.validate_link_types(link_types)
    util.validate_repo_vers(repo_vers)
    util.validate_deletes(deletes)
    util.validate_combines(combines)
    util.validate_local_dirs(local_dirs)

    prog = progress.Progress()  # callbacks talk to this object
    manager = multiprocessing.Manager()
    queue = manager.Queue()
    processes = []

    def signal_handler(signum, frame):
        """ Inner method for terminating threads on signal events.

        This method uses os.kill() to send a SIGKILL directly to the process ID
        because the child processes are running blocking calls that will likely
        take a long time to complete.
        """
        log('Caught exit signal - aborting')
        while len(processes) > 0:
            for p in processes:
                os.kill(p.pid, signal.SIGKILL)
                if not p.is_alive():
                    processes.remove(p)
        sys.exit(1)  # safe to do exit() here because we are a worker

    # Catch user-cancelled or killed signals to terminate threads.
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    for obj_repo in obj_repos:
        checksum = checksums.pop(0)
        stable = stable_vers.pop(0)
        delete = deletes.pop(0)
        link_type = link_types.pop(0)
        version = repo_vers.pop(0)
        combine = combines.pop(0)
        local_dir = local_dirs.pop(0)
        if "symlink" == link_type:
            delete = False  # versioned symlinked repos should not be deleted
        prog.update(obj_repo.id)  # Add the repo to the progress object
        yumcallback = progress.YumProgress(obj_repo.id, queue, callback)
        repocallback = progress.ProgressCallback(queue, callback)
        dest = os.path.join(base_dir, util.friendly(obj_repo.id))
        if local_dir:
            target = repo.localsync
            args = (obj_repo, dest, local_dir, checksum, version, stable,
                    link_type, delete, combine, repocallback)
        else:
            target=repo.sync
            args = (obj_repo, dest, checksum, version, stable, link_type,
                    delete, combine, yumcallback, repocallback)
        p = multiprocessing.Process(target=target, args=args)
        p.start()
        processes.append(p)

    while len(processes) > 0:
        # If data is waiting in the queue from the workers, process it. This
        # needs to be done in the current scope so that one progress object may
        # hold all of the results. (This might be easier with Python 3's
        # nonlocal keyword).
        while not queue.empty():
            e = queue.get()
            if not 'action' in e:
                continue
            if e['action'] == 'repo_init' and 'value' in e:
                prog.update(e['repo_id'], set_total=e['value'])
            elif e['action'] == 'download_end' and 'value' in e:
                prog.update(e['repo_id'], pkgs_downloaded=e['value'])
            elif e['action'] == 'repo_metadata':
                prog.update(e['repo_id'], repo_metadata=e['value'])
            elif e['action'] == 'repo_error':
                prog.update(e['repo_id'], repo_error=e['value'])
            elif e['action'] == 'local_pkg_exists':
                prog.update(e['repo_id'], pkgs_downloaded=1)
            elif e['action'] == 'link_pkg':
                prog.update(e['repo_id'], pkgs_downloaded=1)
            elif e['action'] == 'repo_complete':
                pass # should already know this, but handle it anyways.
            elif e['action'] == 'delete_pkg':
                pass
            elif e['action'] == 'repo_group_data':
                pass
        for p in processes:
            if not p.is_alive():
                processes.remove(p)

    # Return tuple (#repos, #fail, elapsed time)
    return (len(obj_repos), prog.totals['errors'], prog.elapsed())
