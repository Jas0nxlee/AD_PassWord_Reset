import logging
import threading
from concurrent.futures import ThreadPoolExecutor


class EmailDispatcher:
    """带有容量限制的进程内邮件任务执行器。"""

    def __init__(self, workers=2, queue_limit=100, asynchronous=True):
        self.asynchronous = asynchronous
        self.logger = logging.getLogger(__name__)
        self._capacity = threading.BoundedSemaphore(queue_limit)
        self._executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix='email')

    def submit(self, function, *args):
        if not self.asynchronous:
            function(*args)
            return True
        if not self._capacity.acquire(blocking=False):
            self.logger.error('Email task queue is full')
            return False
        self._executor.submit(self._run, function, args)
        return True

    def _run(self, function, args):
        try:
            function(*args)
        except Exception as exc:
            self.logger.error('Email task failed (%s)', type(exc).__name__)
        finally:
            self._capacity.release()
