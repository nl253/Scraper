#!/usr/bin/env python
# -*- coding: utf-8 -*-

# TODO
# 1. make sure there is one thread that yields the results and goes to sleep if
#   there aren't any
# 3. rethink the logic
# 4. possibly use Pool
# 5. get rid of deadlocks, fix it
# 6. use requests if it helps
# 7. parsing with lxml, it's faster
# 8. output with sqlite3 or redis or mongo or mysql or csv
# 9. implement a timeout, use the time module
# 10. join relative URLs
# 11.

from typing import Tuple, List
from urllib.error import HTTPError, URLError
from http.client import RemoteDisconnected, IncompleteRead
import logging
from http_tools import HTMLWrapper
from lexical import HTMLAnalyser
# from lexical import DocumentAnalayzer
from socket import timeout
from ssl import CertificateError
from multiprocessing import cpu_count, Process
from multiprocessing import Queue as SharedQueue
from multiprocessing import Semaphore, current_process
from multiprocessing.managers import SyncManager
from time import sleep, localtime
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
    def __init__(self, starting_urls: List[str] = ["http://www.independent.co.uk/",
                                                   "http://www.telegraph.co.uk/"],
                 themes: List[str] = [],
                 max_results: int = 1000,
                 timeout: int = 3,
                 match_threshold=12,
                 max_threads:
                 int = cpu_count()):

        # settings
        assert max_threads >= 2, 'You need to allow for a minimum of 2 threads.'
        self._max_threads = max_threads

        assert max_results > 0, 'Max entries needs to be a natural number.'
        self._max_results = max_results

        self._timeout = timeout

        self._themes = themes

        # min matches on a page to add entries and links
        self._match_threshold = match_threshold

        # stack to store crawled data as tuples
        self._results = SharedQueue()

        # initialise
        self._manager = SyncManager()
        self._manager.start()

        self._sites_to_crawl = SharedQueue()

        self._yielded_results = self._manager.Value(c_int32, 0)

        # initial URLs, prevent duplication
        for url in set(starting_urls):
            self._sites_to_crawl.put(url)
        self._processed_urls = self._manager.list()
        self._counting_semaphore = Semaphore(self._max_threads)
        general_log.debug('Spider created')
        general_log.info("Max entries set to {}".format(max_results))
        general_log.info("Themes set to {}".format(themes))
        general_log.info("Max threads set to {}".format(max_threads))
        general_log.info("Match threshold set to {}".format(match_threshold))

    def _add_entry(self, *data: str):
        curr_proc = current_process().name
        general_log.debug('{}: Adding an entry, Entries atm: {}'.format(curr_proc, self._results.qsize()))
        self._results.put(tuple(data))


    def crawl(self):

        proc_name = current_process().name

        jobs = []

        timer = localtime().tm_min

        while True:

            # done
            if self._yielded_results.value >= self._max_results:
                break

            # timeout
            elif (localtime().tm_min - timer > self._timeout):
                  general_log.warning('Timout')
                  break

            # not done yet
            # we have semaphores - assign a job
            elif self._counting_semaphore.get_value() > 0:

                general_log.warning('{}: Semaphore free, starting another job, '.format(proc_name))

                job = Process(target=self._crawl)

                # store in a list to keep track and kill
                jobs.append(job)

                # start the last job on list
                jobs[jobs.index(job)].start()

            else:
                while not self._results.empty():
                    self._yielded_results.value += 1
                    yield self._results.get()

                general_log.warning('{}: successfully yielded {} / {} (max), entries atm: {} '.
                                    format(
                                        proc_name,
                                        self._yielded_results.value,
                                        self._max_results,
                                        self._results.qsize()))

                sleep(10)

        ###################################################################################

        # report
        general_log.warning('{}: successfully yielded {} / {}'.format(proc_name, self._yielded_results.value, self._max_results))

        # kill remaining jobs, must be done here, in the main thread
        general_log.warning('{}: killing jobs'.format(proc_name))


        # when done
        for job in jobs:
            if job.is_alive:
                general_log.warning('{}: killing job {}'.format(proc_name, job.name))
                sleep(2)
                job.terminate()
            else:
                general_log.warning('{}: {} already dead'.format(proc_name, job.name))

        # when esceped from the loop
        general_log.warning('{}: Scraping finished, all jobs dead'.format(proc_name))


    def _crawl(self):
        """To be run by each process thread.
        At the end the semaphore is released.
        """

        # HELPER VARIABLES
        proc_name = current_process().name

        self._counting_semaphore.acquire()

        general_log.warning('{}: Semaphore acquired by a crawler'.format(current_process().name))

        while (self._yielded_results.value + self._results.qsize()) < self._max_results:

            general_log.info('{}: {} URLs to crawl, {} / {} processed'.
                             format(proc_name,
                                    self._sites_to_crawl.qsize(),
                                    len(self._processed_urls),
                                    self._max_results))

            focus_url = self._sites_to_crawl.get()

            general_log.info('{}: Focus URL: {}'.format(proc_name, focus_url))

            # add to traversed to prevent visitng twice
            self._processed_urls.append(focus_url)

            try:
                # instantiate an extractor object
                extractor = HTMLWrapper(focus_url)

                if extractor.message != 'OK':
                    general_log.debug('{}: Message from {} was not "OK", continuing'.format(proc_name, extractor))
                    continue

                # count matches on the focus page
                matches = HTMLAnalyser(extractor.HTML, self._themes).theme_count if self._themes else self._match_threshold + 1

            except (IncompleteRead,HTTPError,URLError,RemoteDisconnected,UnicodeDecodeError,UnicodeEncodeError,timeout,CertificateError) as e:
                general_log.error('{}: {} while requesting a response from {}'.format(proc_name, e, focus_url))
                # general_log.error('{}: {}'.format(proc_name, extract_tb(sys.last_traceback)[-1]))
                general_log.debug('{}: Continuing'.format(proc_name))
                continue


            if matches >= self._match_threshold:

                if (self._yielded_results.value + self._results.qsize()) < self._max_results and type(extractor.HTML) is str and len(extractor.HTML) > 10:

                    general_log.debug('{}: Enough matches ({}), adding {}, it\'s content and extracting links'.format(proc_name, matches, focus_url))
                    crawl_log.info('{}: Enough matches ({}), adding {}, it\'s content and extracting links'.format(proc_name, matches, focus_url))

                    # add a tuple (url: str, HTML: str)
                    self._add_entry(focus_url, extractor.HTML)

                # done
                elif self._yielded_results.value + self._results.qsize() >= self._max_results:
                    break

                else:
                    continue

                # ensure you only traverse once
                general_log.debug('{}: Enqueuing filtered, not-traversed links'.format(proc_name))

                # check for titles if they match any of the themes
                if not self._sites_to_crawl.qsize() >= self._timeout * 1000:

                    links = filter(lambda link: link not in self._processed_urls, extractor.URLs)

                    for link in links:
                        self._sites_to_crawl.put_nowait(link)
                else:
                    general_log.debug('{}: {} URLs collected, cap reached, they weren\'t collected'.format(proc_name, self._sites_to_crawl.qsize()))

            else:
                general_log.debug('{}: Not enough matches in {}, continuing'.format(proc_name, focus_url))

        general_log.warning('{}: crawler is relasing a semaphore'.format(proc_name))
        self._counting_semaphore.release()
