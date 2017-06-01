#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Tuple, List
from urllib.error import HTTPError, URLError
from http.client import RemoteDisconnected, IncompleteRead
import logging
from http_tools import HTMLExtractor
from lexical import HTMLAnalyser
# from lexical import DocumentAnalayzer
from socket import timeout
from ssl import CertificateError
from multiprocessing import cpu_count, Process
from multiprocessing import Queue as SharedQueue
from multiprocessing import Semaphore, current_process, Lock
from multiprocessing.managers import SyncManager
from time import sleep
from ctypes import c_int32

logging.basicConfig(
    level=logging.DEBUG,
    filemode='w',
    format='%(threadName)s %(module)s %(levelname)s : %(asctime)s : %(lineno)s : %(message)s.',
    datefmt="%M:%S")

# GENERAL
general_log = logging.getLogger(name=__name__)

# LOG crawled WEBSITES
crawl_log = logging.getLogger(name='crawled')
crawl_log_handler = logging.FileHandler('crawled.log')
crawl_log_handler.setFormatter(logging.Formatter('%(message)s.'))
crawl_log.addHandler(crawl_log_handler)

# INFO for progress
file_info_handler = logging.FileHandler('pylog.log')
file_info_handler.setFormatter(logging.Formatter('%(threadName)s %(module)s %(levelname)s : %(asctime)s : %(lineno)s : %(message)s.'))
file_info_handler.setLevel(logging.INFO)

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
    def __init__(self, starting_urls: List[str], themes: List[str],
                 max_entries=2000, match_threshold=18, max_threads=cpu_count()):
        self._manager = SyncManager()
        self._manager.start()
        # settings
        self._max_entries = max_entries
        self._max_threads = max_threads
        self._themes = themes
        self._entry_access_lock = Lock()
        # min matches on a page to add entries and links
        self._match_threshold = match_threshold
        # stack to store crawled data as tuples
        self._entries = SharedQueue()
        self._to_be_crawled = SharedQueue(20000)
        self._jobs = []
        self._yielded_results = self._manager.Value(c_int32, 0)
        for url in starting_urls:
            self._to_be_crawled.put(url)
        # efficient lookup
        self._processed_urls = self._manager.list()
        self._counting_semaphore = Semaphore(self._max_threads)
        general_log.debug('Spider created')
        general_log.info("Max entries set to {}".format(max_entries))
        general_log.info("Themes set to {}".format(themes))
        general_log.info("Max threads set to {}".format(max_threads))
        general_log.info("Match threshold set to {}".format(match_threshold))

    def _add_entry(self, *data: str):
        curr_proc = current_process().name
        general_log.debug('{}: Adding an entry, Entries atm: {}'.format(curr_proc, self._entries.qsize()))
        self._entries.put(tuple(data))


    def crawl(self):

        proc_name = current_process().name

        general_log.warning('{}: Setting a lock on access to entries'.format(proc_name))

        self._entry_access_lock.acquire()

        while self._yielded_results.value < self._max_entries and self._to_be_crawled.qsize() > 0:

            if self._counting_semaphore.get_value() > 0:
                self._counting_semaphore.acquire()
                general_log.warning('{}: Semaphore acquired, starting another job'.format(proc_name))
                job = Process(target=self._crawl)
                self._jobs.append(job)
                self._jobs[len(self._jobs) - 1].start()

            else:
                while not self._entries.empty():
                    self._yielded_results.value += 1
                    yield self._entries.get()
                general_log.warning('{}: Results are empty, {} already yielded, going to sleep'.format(proc_name, self._yielded_results.value))
                sleep(10)

        # kill remaining jobs, must be done here, in the main thread
        for job in self._jobs:
            job.terminate()

        # when esceped from the loop
        general_log.warning('{}: Scraping finished, all jobs dead, releasing a lock on access to entries'.format(proc_name))
        self._entry_access_lock.release()

    def _crawl(self):
        """To be run by each process thread.
        At the end the semaphore is released.
        """

        # HELPER VARIABLES
        proc_name = current_process().name
        duplicate_traversals = 0
        no_match_counter = 0

        while (self._yielded_results.value + self._entries.qsize()) < self._max_entries and self._to_be_crawled.qsize() > 0:

            general_log.info('{}: {} URLs to crawl'.format(proc_name, self._to_be_crawled.qsize()))
            general_log.info('{}: {} already processed'.format(proc_name, len(self._processed_urls)))

            # get next from from queue
            focus_url = self._to_be_crawled.get()

            if focus_url in self._processed_urls:
                duplicate_traversals += 1
                if duplicate_traversals >= 5:
                    general_log.warning('{}: >= 5 duplicate traversals, breaking'.format(proc_name))
                    break
                else:
                    general_log.warning('{}: current URL {} has already been processed, continuing'.format(proc_name, focus_url))
                    continue

            general_log.info('{}: Focus URL: {}'.format(proc_name, focus_url))

            # add to traversed to prevent visitng twice
            self._processed_urls.append(focus_url)

            try:
                # instantiate an extractor object
                extractor = HTMLExtractor(focus_url)

                if extractor.message != 'OK':
                    general_log.debug('{}: Message from {} was not "OK", continuing'.format(proc_name, extractor))
                    continue

                # count matches on the focus page
                matches = HTMLAnalyser(extractor.HTML, self._themes).theme_count

            except (IncompleteRead,HTTPError,URLError,RemoteDisconnected,UnicodeDecodeError,UnicodeEncodeError,timeout,CertificateError) as e:
                general_log.error('{}: {} while requesting a response from {}'.format(proc_name, e, focus_url))
                # general_log.error('{}: {}'.format(proc_name, extract_tb(sys.last_traceback)[-1]))
                general_log.debug('{}: Continuing'.format(proc_name))
                continue


            if matches >= self._match_threshold:

                if (self._yielded_results.value + self._entries.qsize()) < self._max_entries:

                    general_log.debug('{}: Enough matches ({}), adding {}, it\'s content and extracting links'.format(proc_name, matches, focus_url))
                    crawl_log.info('{}: Enough matches ({}), adding {}, it\'s content and extracting links'.format(proc_name, matches, focus_url))

                    self._add_entry(focus_url, extractor.HTML)

                else:
                    break

                # ensure you only traverse once
                general_log.debug('{}: Enqueuing filetered, not-traversed links'.format(proc_name))

                # check for titles if they match any of the themes
                links = filter(lambda link: link not in self._processed_urls, extractor.URLs)

                for link in links:
                    self._to_be_crawled.put(link)

            elif matches == 0:
                no_match_counter += 1
                if no_match_counter >= 5:
                    general_log.debug('{}: 5 >= websites in a row had no matches, breaking'.format(proc_name))
                    break

            else:
                general_log.debug('{}: Not enough matches in {}, continuing'.format(proc_name, focus_url))

        general_log.warning('{}: relasing a semaphore'.format(proc_name))
        self._counting_semaphore.release()
