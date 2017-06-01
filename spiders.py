#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Tuple, Union, List
from urllib.error import HTTPError, URLError
from http.client import RemoteDisconnected, IncompleteRead
import logging
from http_tools import HTMLExtractor
from lexical import HTMLAnalyser, DocumentAnalayzer
from socket import timeout
from ssl import CertificateError
from multiprocessing import cpu_count, Process
from multiprocessing import Queue as SharedQueue
from multiprocessing import Semaphore, current_process, Lock
from time import sleep

logging.basicConfig(
    level=logging.DEBUG,
    filemode='w',
    format='%(threadName)s %(module)s %(levelname)s : %(asctime)s : %(lineno)s : %(message)s.',
    datefmt="%M:%S")

# GENERAL
general_log = logging.getLogger(name=__name__)

# LOG SCRAPED WEBSITES
scrape_log = logging.getLogger(name='scraped')
scrape_log_handler = logging.FileHandler('scraped.log')
scrape_log_handler.setFormatter(logging.Formatter('%(message)s.'))
scrape_log.addHandler(scrape_log_handler)

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


general_log.addHandler(file_info_handler)
general_log.addHandler(warning_stream_handler)
general_log.addHandler(error_stream_handler)
general_log.addHandler(critical_stream_handler)

# crawl_log = logging.getLogger(name="crawl_logger", )

Entry = Tuple[Union[str, float, float, str], ...]

class Spider():
    def __init__(self, starting_urls: List[str], themes: List[str],
                 max_entries=2000, match_threshold=18, max_threads=cpu_count(),
                 process_results_with=None, function_args=[]):
        # settings
        self._max_entries = max_entries
        self._max_threads = max_threads
        self._themes = themes
        self._entry_access_lock = Lock()
        # min matches on a page to add entries and links
        self._match_threshold = match_threshold
        # stack to store scraped data as tuples
        self._entries = SharedQueue()
        self._to_be_scraped = SharedQueue(20000)
        self._jobs = []
        for url in starting_urls:
            self._to_be_scraped.put(url)
        # efficient lookup
        self._processed_urls = set()
        self._counting_semaphore = Semaphore(self._max_threads)
        self._finished = False  # initialise to False
        self._function = process_results_with
        self._function_args = function_args
        assert type(function_args) is list, 'Extra args need to be passed as list.'
        general_log.debug('Spider created')
        general_log.info("Max entries set to {}".format(max_entries))
        general_log.info("Themes set to {}".format(themes))
        general_log.info("Max threads set to {}".format(max_threads))
        general_log.info("Match threshold set to {}".format(match_threshold))

    def _add_entry(self, *entry: Entry):
        curr_proc = current_process().name
        if self._function:
            if self._function_args:
                # if you supply your own funct to process the data, you need to
                # make sure it outputs a tuple
                entry = self._processing_func(*entry, *self._function_args)
            else:
                entry = self._processing_func(*entry)
        else:
            entry = tuple(entry)
        assert type(entry) is tuple, 'Type of entry is not tuple.'
        general_log.debug('{}: Adding an entry'.format(curr_proc))
        self._entries.put(entry)
        general_log.info('{}: No Entries: {}'.format(curr_proc, self._entries.qsize()))

    @property
    def ientries(self) -> Entry:

        self._entry_access_lock.acquire()

        while not self._entries.empty():
            yield self._entries.get()

        self._entry_access_lock.release()

    def scrape(self):

        proc_name = current_process().name

        general_log.warning('{}: Setting a lock on access to entries'.format(proc_name))

        self._entry_access_lock.acquire()

        while self._entries.qsize() < self._max_entries and self._to_be_scraped.qsize() > 0:

            if self._counting_semaphore.acquire():
                general_log.warning('{}: Semaphore acquired, starting another job'.format(proc_name))
                job = Process(target=self._scrape)
                self._jobs.append(job)
                self._jobs[len(self._jobs) - 1].start()

            else:
                general_log.warning('{}: Going to sleep'.format(proc_name))
                sleep(10)

        # # once we have enough entries
        # while not all(map(lambda job: not job.is_alive(), self._jobs)):
            # for job in self._jobs:
                # if job.is_alive():
                    # general_log.warning('{}: job {} is still alive despite {} entries, going to sleep'.format(proc_name, job.name, self._entries.qsize()))
                    # general_log.warning('{}: Current jobs: {} '.format(proc_name, self._jobs))
                    # sleep(10)

        for job in self._jobs:
            job.terminate()

        # set finished when esceped from the loop

        general_log.warning('{}: All jobs dead, setting finished to True'.format(proc_name))

        self._finished = True

        general_log.warning('{}: Scraping finished, releasing a lock on access to entries'.format(proc_name))
        self._entry_access_lock.release()

    @property
    def finished(self) -> bool:
        return self._finished

    def _scrape(self):
        """To be run by each process thread.
        At the end the semaphore is realsed and process terminates itself.
        """
        # loop until the queue is empty
        # assert type(self._to_be_scraped) is , 'Type of self._to_be_scraped is not Counter!'

        proc_name = current_process().name

        while self._entries.qsize() < self._max_entries and self._to_be_scraped.qsize() > 0:

            general_log.info('{}: {} URLs to scrape'.format(proc_name, self._to_be_scraped.qsize()))
            general_log.info('{}: {} already processed'.format(proc_name, len(self._processed_urls)))

            # get next from from queue
            focus_url = self._to_be_scraped.get()

            if focus_url in self._processed_urls:
                general_log.warning('{}: current URL {} has already been processed, continuing'.format(proc_name, focus_url))
                continue

            general_log.info('{}: Focus URL: {}'.format(proc_name, focus_url))

            # add to traversed to prevent visitng twice
            self._processed_urls.add(focus_url)

            try:
                # instantiate an extractor object
                extractor = HTMLExtractor(focus_url)
                if extractor.message != 'OK':
                    general_log.debug('{}: Message from {} was not "OK", continuing'.format(proc_name, extractor))
                    continue
                # get no matches in html
                matches = HTMLAnalyser(extractor.HTML, self._themes).theme_count

            except (IncompleteRead,HTTPError,URLError,RemoteDisconnected,UnicodeDecodeError,UnicodeEncodeError,timeout,CertificateError) as e:
                general_log.error('{}: {} while requesting a response from {}'.format(proc_name, e, focus_url))
                # general_log.error('{}: {}'.format(proc_name, extract_tb(sys.last_traceback)[-1]))
                general_log.debug('{}: Continuing'.format(proc_name))
                continue

            # count matches on the focus page

            if matches >= self._match_threshold:

                scrape_log.info('{}: Found {} matches in the content of {}'.format(proc_name, matches, focus_url))
                general_log.debug('{}: Found {} matches in the content of {}'.format(proc_name, matches, focus_url))

                general_log.debug('Enough matches, adding results and extracting links')

                general_log.info('{}: Adding results from {} to entries'.format(proc_name, focus_url))
                for sent in DocumentAnalayzer(extractor.text, themes=self._themes).matching_sents:
                    if self._entries.qsize() < self._max_entries:
                        self._add_entry(focus_url, sent)
                    else:
                        break

                # ensure you only traverse once
                general_log.debug('{}: Adding filetered, not-traversed links'.format(proc_name))

                # check for titles if they match any of the themes
                links = filter(lambda link: link not in self._processed_urls, extractor.URLs)

                for link in links:
                    self._to_be_scraped.put(link)

            else:
                general_log.debug('{}: Not enough matches in {}, continuing'.format(proc_name, focus_url))

        general_log.warning('{}: relasing a semaphore'.format(proc_name))
        self._counting_semaphore.release()
