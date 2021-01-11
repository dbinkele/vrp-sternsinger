import os
import signal
import errno
import random

import rq.queue
from rq.worker import signal_name, StopRequested, logger as rq_logger

IMMINENT_SHUTDOWN_DELAY = 6


class ShutDownImminentException(Exception):
    def __init__(self, msg, extra_info):  # pragma: no cover
        self.extra_info = extra_info
        super(ShutDownImminentException, self).__init__(msg)


def handle_shutdown_imminent(signum, frame):  # pragma: no cover
    del_secs = IMMINENT_SHUTDOWN_DELAY
    if del_secs == 0:
        rq_logger.warn('Imminent shutdown, raising ShutDownImminentException immediately')
        force_shutdown(signum, frame)
    else:
        rq_logger.warn('Imminent shutdown, raising ShutDownImminentException in %d seconds' % del_secs)
        signal.signal(signal.SIGALRM, force_shutdown)
        signal.alarm(del_secs)


def force_shutdown(signum, frame):  # pragma: no cover
    info = {attr: getattr(frame, attr) for attr in ['f_code', 'f_exc_traceback', 'f_exc_type', 'f_exc_value',
                                                    'f_lasti', 'f_lineno', 'f_locals', 'f_restricted', 'f_trace']}
    rq_logger.warn('raising ShutDownImminentException to cancel job...')
    raise ShutDownImminentException('shut down imminent (signal: %s)' % signal_name(signum), info)


class Worker(rq.Worker):
    """
    Modified version of rq worker which:
    * stops work horses getting killed with SIGTERM
    * sends SIGRTMIN to work horses on SIGTERM to the main process so they can crash as they wish

    Note: coverage doesn't work inside the forked thread so code expected to be processed there has pragma: no cover
    """

    def main_work_horse(self, job):  # pragma: no cover
        """
        This is the entry point of the newly spawned work horse.

        It's behavior is altered from the default to ignore SIGTERM signals
        """
        random.seed()

        signal.signal(signal.SIGRTMIN, handle_shutdown_imminent)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)

        self._is_horse = True
        self.log = rq_logger

        success = self.perform_job(job)
        os._exit(int(not success))

    def _install_signal_handlers(self):
        """
        Modified to force shutdown of the worker by handling SIGTERM with request_force_stop the first time it's
        fired.

        Modified to set a signal to send SIGRTMIN to horse process when the first SIGTERM is received
        """

        # noinspection PyUnusedLocal
        def request_force_stop(signum, frame):  # pragma: no cover (this is unchanged from library version)
            """Terminates the application (cold shutdown).
            """
            self.log.warning('Cold shut down')

            # Take down the horse with the worker
            if self.horse_pid:
                msg = 'Taking down horse {0} with me'.format(self.horse_pid)
                self.log.debug(msg)
                try:
                    os.kill(self.horse_pid, signal.SIGKILL)
                except OSError as e:
                    # ESRCH ("No such process") is fine with us
                    if e.errno != errno.ESRCH:
                        self.log.debug('Horse already down')
                        raise
            raise SystemExit()

        # noinspection PyUnusedLocal
        def request_stop(signum, frame):
            """Stops the current worker loop but waits for child processes to
            end gracefully (warm shutdown).
            """
            self.log.debug('Got signal {0}'.format(signal_name(signum)))

            signal.signal(signal.SIGINT, request_force_stop)
            signal.signal(signal.SIGTERM, request_force_stop)

            # start of change from library version {
            if self.horse_pid != 0:
                self.log.warning('Warm shut down requested, sending horse SIGRTMIN signal')
                try:
                    os.kill(self.horse_pid, signal.SIGRTMIN)
                except OSError as e:
                    if e.errno != errno.ESRCH:  # pragma: no cover
                        self.log.debug('Horse already down')
                        raise
            else:
                self.log.warning('Warm shut down requested, no horse found')
            # } end of change from library version

            # If shutdown is requested in the middle of a job, wait until
            # finish before shutting down
            if self.get_state() == 'busy':
                self._stop_requested = True
                self.log.debug('Stopping after current horse is finished. '
                               'Press Ctrl+C again for a cold shutdown.')
            else:
                raise StopRequested()

        signal.signal(signal.SIGINT, request_stop)
        signal.signal(signal.SIGTERM, request_stop)