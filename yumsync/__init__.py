import os
import sys
import multiprocessing
import signal
import urlparse
from yumsync import util, progress
from yumsync.log import log
from yumsync.version import __version__

def sync(repos=[], callback=None):
    """ Mirror repositories with configuration data from multiple sources.

    Handles all input validation and higher-level logic before passing control
    on to threads for doing the actual syncing. One thread is created per
    repository to alleviate the impact of slow mirrors on faster ones.
    """

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
        sys.exit(1) # safe to do exit() here because we are a worker

    # Catch user-cancelled or killed signals to terminate threads.
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    for repo in repos:
        prog.update(repo.id) # Add the repo to the progress object
        yumcallback = progress.YumProgress(repo.id, queue, callback)
        repocallback = progress.ProgressCallback(queue, callback)

        repo.set_yum_callback(yumcallback)
        repo.set_repo_callback(repocallback)

        p = multiprocessing.Process(target=repo.sync)
        processes.append(p)
        p.start()

    while len(processes) > 0:
        # If data is waiting in the queue from the workers, process it. This
        # needs to be done in the current scope so that one progress object may
        # hold all of the results. (This might be easier with Python 3's
        # nonlocal keyword).
        while not queue.empty():
            e = queue.get()
            if not 'action' in e:
                continue
            if e['action'] == 'repo_init' and 'data' in e:
                prog.update(e['repo_id'], set_total=e['data'][0])
            elif e['action'] == 'download_end' and 'data' in e:
                prog.update(e['repo_id'], pkgs_downloaded=e['data'][0])
            elif e['action'] == 'repo_metadata' and 'data' in e:
                prog.update(e['repo_id'], repo_metadata=e['data'][0])
            elif e['action'] == 'repo_error' and 'data' in e:
                prog.update(e['repo_id'], repo_error=e['data'][0])
            elif e['action'] == 'pkg_exists':
                prog.update(e['repo_id'], pkgs_downloaded=1)
            elif e['action'] == 'link_local_pkg':
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
    return (len(repos), prog.totals['errors'], prog.elapsed())
