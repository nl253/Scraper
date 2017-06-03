#!/usr/bin/env python
# -*- coding: utf-8 -*-

# TODO
# 1. export module
#   - output with
#           * sqlite3
#           * redis
#           * mongo
#           * mysql
#           * csv
#
# 2. expand the analysis module
#   - parsing with lxml, it's faster
#    (but use regex for simple tasks
#     because it's faster than both)
#
# 3.


from typing import Tuple, List, Iterable
from urllib.error import HTTPError, URLError
from http.client import RemoteDisconnected, IncompleteRead
import logging
from analysis import HTMLAnalyser
from socket import timeout
from ssl import CertificateError
from multiprocessing import cpu_count, Process
from multiprocessing import Condition as ProcessCondition
from multiprocessing import Queue as SharedProcessQueue
from multiprocessing import current_process, active_children
from multiprocessing import Semaphore as ProcessSemaphore
from multiprocessing.managers import SyncManager as ProcessSyncManager
from logging import getLogger
from signal import pthread_kill
import threading
from threading import current_thread
from queue import Empty, Full
# from concurrent.futures import ThreadPoolExecutor
from threading import Lock as ThreadLock
from threading import Condition as ThreadCondition
from threading import Semaphore as ThreadSemaphore
from time import sleep
from ctypes import c_int32, c_float

logging.basicConfig(
    level=logging.DEBUG,
    filemode='w',
    format='%(processName)s %(threadName)s %(module)s %(levelname)s [%(asctime)s] [%(lineno)s] %(message)s.',
    datefmt="%M:%S")

# GENERAL
general_log = getLogger(name=__name__)

# LOG crawled WEBSITES
crawl_log = getLogger(name='crawled')
crawl_log_handler = logging.FileHandler('crawled.log')
crawl_log_handler.setFormatter(logging.Formatter('%(message)s.'))
crawl_log.addHandler(crawl_log_handler)

# INFO for progress
file_info_handler = logging.FileHandler('pylog.log')
file_info_handler.setFormatter(logging.Formatter(
    '%(processName)s %(threadName)s %(module)s %(levelname)s [%(asctime)s] [%(lineno)s] %(message)s.'))
file_info_handler.setLevel(logging.DEBUG)

# WARNING
warning_stream_handler = logging.StreamHandler()
warning_stream_handler.setLevel(logging.CRITICAL)

# ERROR for serious
error_stream_handler = logging.StreamHandler()
error_stream_handler.setLevel(logging.ERROR)

# CRITICAL
critical_stream_handler = logging.StreamHandler()
critical_stream_handler.setLevel(logging.CRITICAL)

# ASSIGN HANDLERS
general_log.addHandler(file_info_handler)
general_log.addHandler(warning_stream_handler)
general_log.addHandler(error_stream_handler)
general_log.addHandler(critical_stream_handler)

Result = Tuple[str, str]

class Spider():
    """Asynchronous, multithreading and multiprocessing iterable spider.
    """
    def __init__(self, starting_urls: Iterable[str] = ["http://www.independent.co.uk/",
                                                   "http://www.telegraph.co.uk/"],
                 themes: List[str] = [],
                 max_results: int = 1000,
                 timeout: int = 3000,
                 match_threshold=12,
                 max_queue_size: int = 1000,
                 max_child_processes: int = 3,
                 empty_links_queue_timeout: int = 30,
                 max_threads: int = cpu_count()):

        # settings
        self._max_queue_size = max_queue_size

        assert max_threads >= 2, 'You need to allow for a minimum of 2 threads.'
        self._max_threads: int = max_threads

        self._max_child_proc: int = max_child_processes

        assert max_results > 0, 'Max entries needs to be a natural number.'
        self._max_results: int = max_results

        assert timeout > 200, 'Timout needs to be above 200'
        self._timeout: int = timeout

        self._themes: List[str] = themes

        assert empty_links_queue_timeout > 10, 'Empty links-queue timout needs to be above 10'
        self._no_links_timout: int = empty_links_queue_timeout

        # min matches on a page to add entries and links
        self._match_threshold: int = match_threshold

        # initialise
        self._manager = ProcessSyncManager()
        self._manager.start()

        # stack to store crawled data as tuples
        self._results = SharedProcessQueue(self._max_results)

        self._sites_to_crawl = SharedProcessQueue(self._max_queue_size)

        self._yielded_counter = self._manager.Value(c_int32, 0)

        # initial URLs, prevent duplication
        for url in set(starting_urls):
            self._sites_to_crawl.put(url)

        self._processed_urls = self._manager.list()
        self._inactive_children = ProcessSemaphore(self._max_child_proc)

    def _add_entry(self, *data: str):
        """Used by child processes to add gathered entries into temp storage (self._results: SharedProcessQueue).
        """
        general_log.debug(
            f'{current_process().name} {current_thread().name} Adding an entry, Entries atm: {self._results.qsize()}')
        self._results.put(tuple(data))

    def crawl(self):
        """The method to be called directly by the user, all others are helper-methods.
        """

        # keep track of active processes to kill later
        children: List[Process] = [Process(target=self._spawn_crawl_proc, name=f"Process {i}") for i in range(self._max_child_proc)]

        # import ipdb; ipdb.set_trace()  # XXX BREAKPOINT

        for child in children:
            general_log.warning('{current_process().name} Starting another working child')
            child.start()
            sleep(5)

        any_results_pending = ProcessCondition()

        # loop while enough results havent been yielded
        while self._yielded_counter.value < self._max_results:
            any_results_pending.acquire()
            # block until there is something to yield
            any_results_pending.wait_for(lambda : self._results.qsize() > 0)
            while not self._results.empty():
                self._yielded_counter.value += 1
                yield self._results.get()

        # report
        general_log.warning(
            f'{current_process().name} Successfully yielded {self._yielded_counter.value} / {self._max_results}')

        # kill remaining children, must be done here, in the main thread
        general_log.warning('{current_process().name} Killing children')

        # when done
        for child in filter(lambda child: not child.is_alive()):
            general_log.warning(f'{current_process().name} Killing child {child.name}')
            sleep(2)
            child.terminate()

        # when esceped from the loop
        general_log.warning(f'{current_process().name} Scraping finished, all children dead')

    def _thread_scrape_next_url(self):

            # keep track of 'queue misses'
            misses = 0

            while self._yielded_counter.value + self._results.qsize() <= self._max_results:

                general_log.warning(f'{current_process().name} {current_thread().name} Yielded {self._yielded_counter.value} / {self._max_results}')

                general_log.warning(f'{current_process().name} {current_thread().name} Produced {self._yielded_counter.value + self._results.qsize()} results out of / {self._max_results}')

                general_log.warning(f'{current_process().name} {current_thread().name} {self._results.qsize()} items waiting to be yielded')

                # fetch next
                general_log.warning(f'{current_process().name} {current_thread().name} Attempting to get another link off the _sites_to_crawl: {self._sites_to_crawl}')
                try:
                    focus_url = self._sites_to_crawl.get()
                    misses = 0  # reset
                except Empty as e:
                    misses += 1
                    if misses > 5:  # 5 times tried to get from queue with no effect, finish thread
                        general_log.warning(
                            f'{current_process().name} {current_thread().name} 5 or more failures to get from self._sites_to_crawl. Breaking')
                        break
                    else:
                        sleep(5)
                        continue

                general_log.warning(f'{current_process().name} {current_thread().name} Focus URL: {focus_url} taken off {self._sites_to_crawl} which has {self._sites_to_crawl.qsize()} items left')

                # add to traversed to prevent visitng twice
                general_log.warning(
                    f'{current_process().name} {current_thread().name} Appending {focus_url} to _processed_urls which accumulated {len(self._processed_urls)} items')
                self._processed_urls.append(focus_url)

                try:
                    # instantiate an analyser object
                    general_log.warning(f'{current_process().name} {current_thread().name} Making an HTMLAnalyser')
                    analyser = HTMLAnalyser(focus_url, self._themes)

                    if analyser.message != 'OK':
                        general_log.debug(f'{current_process().name} {current_thread().name} Message from {focus_url} was not "OK"')
                        continue

                    # count matches on the focus page
                    no_matches = analyser.theme_count
                    general_log.warning(f'{current_process().name} {current_thread().name} Number of matches is {no_matches}')

                except (IncompleteRead,HTTPError,URLError,RemoteDisconnected,UnicodeDecodeError,UnicodeEncodeError,timeout,CertificateError) as e:
                    general_log.error(f'{current_process().name} {current_thread().name} {e} while requesting a response from {focus_url}')
                    continue

                if not no_matches >= self._match_threshold:
                    general_log.info(f'{current_process().name} {current_thread().name} Not enough matches in {focus_url}, continuing')
                    continue

                self._add_entry(focus_url, analyser.HTML)

                if not self._sites_to_crawl.full():
                    # ensure you only traverse once
                    general_log.debug('{current_process().name} {current_thread().name} Enqueuing filtered, not-traversed links')
                    for link in filter(lambda link: link not in self._processed_urls, analyser.URLs):
                        self._sites_to_crawl.put(link)
                else:
                    general_log.warning(f'{current_thread().name} _sites_to_crawl: Queue[str] is full')

            # on break
            general_log.warning(f'{current_thread().name} Enough entries gathered or timout has occured, breaking thread')

    def _spawn_crawl_proc(self):
        """To be run by each process thread.
        At the end the semaphore is released.
        """

        # acquire by the main thread on every child-process on start()
        general_log.warning(f'{current_process().name} {current_thread().name} Attempting to acquire a semaphore by a crawler. Current value: {self._inactive_children.get_value()}')
        self._inactive_children.acquire()
        general_log.warning(f'{current_process().name} {current_thread().name} Semaphore acquired by a crawler. Current value: {self._inactive_children.get_value()}')

        general_log.warning(f'{current_process().name} {current_thread().name} Creating threads')

        threads = [threading.Thread(target=self._thread_scrape_next_url, name=f"Thread {i}") for i in range(self._max_threads)]

        general_log.warning(f'{current_process().name} {current_thread().name} Threads: {threads}')

        for thread in threads:
            general_log.warning(f'{current_process().name} {current_thread().name} Starting thread: {thread.name}')
            sleep(1)  # delay between spawning
            thread.start()

        # the main thread within this child-process acquires a `Lock` which
        # needs to last utill all child-threads finished (dead)
        enough_gathered = ThreadCondition()

        general_log.warning(f'{current_process().name} {current_thread().name} Acquiring enough_gathered condition')

        enough_gathered.acquire()

        general_log.warning(f'{current_process().name} {current_thread().name} Waiting for enough_gathered condition, timeout set to {self._timeout}')

        enough_gathered.wait_for(lambda : self._yielded_counter.value + self._results.qsize() >= self._max_results, timeout=self._timeout)

        for thread in threads:
            general_log.warning(
                f'{current_process().name} {current_thread().name} Enough data produced, killing threads')
            sleep(2)
            pthread_kill(thread.ident)

        general_log.warning('{current_process().name} {current_thread().name} crawler is relasing a semaphore')

        self._inactive_children.release()
