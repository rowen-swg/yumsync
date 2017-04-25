import os
import sys
import multiprocessing
import signal
import urlparse
from yumsync import util, progress
from yumsync.log import log
from yumsync.metadata import __version__

def sync(repos=None, callback=None):
    """ Mirror repositories with configuration data from multiple sources.

    Handles all input validation and higher-level logic before passing control
    on to threads for doing the actual syncing. One thread is created per
    repository to alleviate the impact of slow mirrors on faster ones.
    """

    if repos is None:
        repos = []

    prog = progress.Progress()  # callbacks talk to this object
    manager = multiprocessing.Manager()
    queue = manager.Queue()
    processes = []

    def signal_handler(_signum, _frame):
        """ Inner method for terminating threads on signal events.

        This method uses os.kill() to send a SIGKILL directly to the process ID
        because the child processes are running blocking calls that will likely
        take a long time to complete.
        """
        log('Caught exit signal - aborting')
        while len(processes) > 0:
            for proc in processes:
                os.kill(proc.pid, signal.SIGKILL)
                if not proc.is_alive():
                    processes.remove(proc)
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

        proc = multiprocessing.Process(target=repo.sync)
        processes.append(proc)
        proc.start()

    while len(processes) > 0:
        # If data is waiting in the queue from the workers, process it. This
        # needs to be done in the current scope so that one progress object may
        # hold all of the results. (This might be easier with Python 3's
        # nonlocal keyword).
        while not queue.empty():
            event = queue.get()
            if not 'action' in event:
                continue
            if event['action'] == 'repo_init' and 'data' in event:
                prog.update(event['repo_id'], set_total=event['data'][0])
            elif event['action'] == 'download_end' and 'data' in event:
                prog.update(event['repo_id'], pkgs_downloaded=event['data'][0])
            elif event['action'] == 'repo_metadata' and 'data' in event:
                prog.update(event['repo_id'], repo_metadata=event['data'][0])
            elif event['action'] == 'repo_error' and 'data' in event:
                prog.update(event['repo_id'], repo_error=event['data'][0])
            elif event['action'] == 'pkg_exists':
                prog.update(event['repo_id'], pkgs_downloaded=1)
            elif event['action'] == 'link_local_pkg':
                prog.update(event['repo_id'], pkgs_downloaded=1)
            elif event['action'] == 'repo_complete':
                pass # should already know this, but handle it anyways.
            elif event['action'] == 'delete_pkg':
                pass
            elif event['action'] == 'repo_group_data':
                pass
        for proc in processes:
            if not proc.is_alive():
                processes.remove(proc)

    # Return tuple (#repos, #fail, elapsed time)
    return (len(repos), prog.totals['errors'], prog.elapsed())
