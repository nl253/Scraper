#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# TODO
# 1. export module
#   - output with
#           * sqlite3
#           * csv
#           * mysql
#           * JSON ?
#           * redis ?
#           * mongo ?
#
# 2. expand the analysis module
#   - parsing with lxml, it's faster
#    (but use regex for simple tasks
#     because it's faster than both)

# STDLB
from collections import namedtuple
from ctypes import c_int32, c_float
from http.client import RemoteDisconnected, IncompleteRead
from multiprocessing import Queue as SharedProcessQueue
from multiprocessing import Semaphore as ProcessSemaphore
from multiprocessing import cpu_count, Process
from multiprocessing import current_process, active_children
from multiprocessing.managers import ListProxy, DictProxy
from multiprocessing.managers import SyncManager as ProcessSyncManager
from copy import copy
from multiprocessing.managers import Value as CValue
from queue import Empty
from signal import pthread_kill
from socket import timeout
from ssl import CertificateError
from threading import current_thread, Thread
from threading import local as threadvars
from threading import Timer as ThreadTimer
from time import sleep
from urllib.error import HTTPError, URLError

# OWN
from analysis import HTMLAnalyser, HTMLWrapper

# DEV UTILS
from _test_spiders import SpiderVerifier
from logutils import *
from typing import Tuple, List, Iterable, Union
import logging

class BaseSpider():
    """Asynchronous, multithreading and multiprocessing iterable spider.
    This is a base class that will have many implementations.
    """
    def __init__(self,
                 starting_urls: Iterable[str],
                 max_results: int = 1000,
                 timeout: int = 3000,
                 max_child_processes: int = 3,
                 max_threads: int = cpu_count()):

        # settings
        self._max_threads: int = max_threads
        self._max_children: int = max_children
        self._max_results: int = max_results
        self._timeout: int = timeout

        # initialise
        self._manager: ProcessSyncManager = ProcessSyncManager()
        self._manager.start()

        # store crawled data until yielded
        self._results: SharedProcessQueue = SharedProcessQueue(self._max_results)

        # simulate counter
        self._URLs: DictProxy = self._manager.dict()

        # keep track of how many have been yielded
        self._yielded_counter: CValue = self._manager.Value(c_int32, 0)

        # initial URLs, prevent duplication
        for URL in set(starting_urls):
            self._add_URL(URL)

        self._processed_URLs: ListProxy = self._manager.list()
        self._inactive_children: ProcessSemaphore = ProcessSemaphore(self._max_children)

        # check if OK
        SpiderVerifier(self).verify_constructor()

    @property
    def yielded(self) -> int:
        """The count of items yielded so far.
        """
        return self._yielded_counter.value

    @property
    def max_children(self) -> int:
        """Max child processes.
        """
        return self._max_children

    @max_children.setter
    def max_children(self, new_value):
        self._max_children = new_value

    @property
    def max_results(self) -> int:
        """Max (cap) on the number of results produced by the Spider.
        """
        return self._max_results

    @max_results.setter
    def max_results(self, new_value: int):
        self._max_results = new_value

    @property
    def max_threads(self) -> int:
        """Max threads spawned by each child-process.
        """
        return self._max_threads

    @max_threads.setter
    def max_threads(self, new_value):
        self._max_threads = new_value

    @property
    def timeout(self) -> float:
        """When timout passes the spider will stop crawling.
        """
        return self._timeout

    @timeout.setter
    def timeout(self, new_timeout):
        self._timeout = new_timeout

    @abstractmethod
    @classmethod
    def preprocess(URL: str, HTML: str, headers: dict) -> Tuple[str, str, dict]:
        """Apply to each resutl, needs to have this exact method signature,
        it aims to prepare the gathered data to be yielded.
        """
        proc_thread_debug(f'Preprocessing an result')
        return tuple(URL, HTML, headers)

    def _add_result(self, URL: str, HTML: str, headers: dict):
        """Used by child processes to add gathered entries into temp storage (self._results: SharedProcessQueue).
        The data is passed on to preprocess before adding an result.
        """
        self._results.put(BaseSpider.preprocess(data))
        proc_thread_debug(f'Added an result, Entries atm: {self._results.qsize()}')

    @property
    def processed_URLs(self) -> List[str]:
        return list(copy(self._processed_URLs))

    def crawl(self):
        """The method to be called directly by the user, all others are helper-methods.
        """

        # keep track of active processes to kill later
        children: List[Process] = [Process(target=self._spawn_new_child, name=f"Process {i}") for i in range(self._max_children)]

        for child in children:
            proc_thread_warn(f'Starting another working child')
            child.start()
            sleep(5)

        # loop while enough results havent been yielded
        while self._yielded_counter.value < self._max_results:
            # block until there is something to yield
            if  self._results.qsize() > 0:
                while not self._results.empty():
                    self._yielded_counter.value += 1
                    yield self._results.get()
            else:
                sleep(8)

        # report
        proc_thread_warn(f'{self._yielded_counter.value} / {self._max_results}')

        # kill remaining children, must be done here, in the main thread
        proc_thread_warn(f'Killing children')

        # when done
        for child in filter(lambda child: not child.is_alive()):
            proc_thread_warn(f'Killing child {child.name}')
            sleep(2)
            child.terminate()

        # when esceped from the loop
        proc_thread_warn(f'Scraping finished, all children dead')

    @property
    def URLs(self) -> Iterable[str]:
        return self._URLs.keys()

    def _add_URL(self, URL: str):
        for stored_URL in self._URLs:
            if stored_URL == URL:
                self._URLs[stored_URL] += 1
                return
        self._URLs[URL] = 1

    @property
    def next_URL(self) -> str:
        assert len(self._URLs) > 0, 'No more URLs to get!'
        most_freq = max(self._URLs.values())
        for URL in self._URLs:
            if self._URLs[URL] == most_freq:
                self._processed_URLs.append(URL)
                del(self._URLs[URL])
                proc_thread_warn(
                    f'Appending {focus_url} to _processed_URLs which accumulated {len(self._processed_URLs)} items')
                return URL

    def _thread_scrape_next_url(self):

            # keep track of how many times this thread failed to get next URL
            threadvars.misses = 0

            while self._yielded_counter.value + self._results.qsize() <= self._max_results:

                proc_thread_warn(f'Yielded {self._yielded_counter.value} / {self._max_results}')

                proc_thread_warn(f'Produced {self._yielded_counter.value + self._results.qsize()} results out of / {self._max_results}')

                proc_thread_warn(f'{self._results.qsize()} items waiting to be yielded')

                # fetch next
                proc_thread_warn(f'Attempting to get another link off the _url_queue: {self._url_queue}')

                try:
                    focus_url = self.next_URL
                    threadvars.misses = 0  # reset

                except AssertionError as e:
                    threadvars.misses += 1
                    if threadvars.misses > 5:  # 5 times tried to get from queue with no effect, finish thread
                        proc_thread_warn(
                            f'more than 5 failures to get from self._url_queue. Breaking')
                        break
                    else:
                        sleep(5)
                        continue

                proc_thread_warn(f'Focus URL: {focus_url} taken off URLs which has {len(self.URLs)} items left')

                try:
                    # instantiate an HTMLWrapper object
                    proc_thread_warn(f'Making an HTMLWrapper')
                    wrapper = HTMLWrapper(URL)

                except (IncompleteRead,HTTPError,URLError,RemoteDisconnected,timeout,CertificateError) as e:
                    proc_thread_err(f'{e} while requesting a response from {focus_url}')
                    continue

                except (UnicodeDecodeError,UnicodeEncodeError) as e:
                    proc_thread_err(f'{e} while requesting a response from {focus_url}')
                    continue

                if not self._results.full():
                    if BaseSpider.test_result(wrapper.URL, wrapper.HTML, wrapper.headers):
                        self._add_result(focus_url, wrapper.HTML, wrapper.headers)
                        for URL in wrapper.iURLs:
                            self._try_add_URL(URL)
                else:
                    break


            # on break
            proc_thread_warn(
                f'Enough entries gathered or timout has occured or > 5 failures to get a URL, breaking thread')

    def _safe_to_crawl(self) -> bool:
        """Used to check if it's OK to begin crawling when crawl() is called. For safety.
        """
        raise NotImplementedError

    def _try_add_URL(URL: str) -> bool:
        proc_thread_debug(f'Trying to enque {URL}')

        # ensure you only traverse once
        if len(self._URLs) > 0 and URL not in self.URLs:
            self._add_URL(URL)
            return True
        else:
            return False

    def _spawn_new_child(self):
        """To be run by each process thread.
        At the end the semaphore is released.
        """

        # acquire by the main thread on every child-process on start()
        proc_thread_warn(f'Attempting to acquire a semaphore by a crawler. Current value: {self._inactive_children.get_value()}')

        self._inactive_children.acquire()

        proc_thread_warn(f'Semaphore acquired by a crawler. Current value: {self._inactive_children.get_value()}')

        proc_thread_warn(f'Creating threads')

        threads = [Thread(target=self._thread_scrape_next_url, name=f"Thread {i}") for i in range(self._max_threads)]

        proc_thread_warn(f'Threads: {threads}')

        for thread in threads:
            proc_thread_warn(f'Starting thread: {thread.name}')
            sleep(1)  # delay between spawning
            thread.start()

        def end_thread():
            for thread in threads:
                proc_thread_warn(
                    f'Enough data produced, killing threads')
                sleep(2)
                pthread_kill(thread.ident)

            proc_thread_warn('crawler is relasing a semaphore')

            self._inactive_children.release()


        timer = ThreadTimer(self._timeout, end_thread)
        timer.start()

        while not self._yielded_counter.value + self._results.qsize() >= self._max_results:
            sleep(30)

    @classmethod
    @abstractmethod
    def test_result(URL: str, HTML: str, headers: dict) -> bool:
        """To be overriden by a boolean-return function that takes these exact args.
        This is repetedly applies to all scraped results and determines if
        links from that website should be added to `to be scraped` as well
        as if the website itself ie the html doc will be added as an entry.
        """
        return True


class ThemeSpider(BaseSpider):
    """An implementation of BaseSpider that hunts for themes passed as List[str].
    It will output results as chunks of texts relevant to the themes passed
    to the constructor.
    """
    def __init__(self, starting_urls: Iterable[str],
                 themes: List[str],
                 max_results: int = 1000,
                 timeout: int = 3000,
                 match_threshold = 12,
                 max_child_processes: int = 3,
                 max_threads: int = cpu_count()):

        # ADDED ON TOP OF WHAT WAS IN BASESPIDER
        # hunt for these themes in HTML documents
        self._themes: Iterable[str] = themes

        # min matches on a page to add entries and links
        self._match_threshold: int = match_threshold

        super().__inti__(
            starting_urls,
            max_results,
            timeout,
            max_child_processes,
            max_threads)

    @classmethod
    def test_result(URL: str, HTML: str, headers: dict) -> bool:

        try:
            # instantiate an analyser object
            proc_thread_warn(f'Making an HTMLAnalyser')
            analyser = HTMLAnalyser(URL)

            # count matches on the focus page
            no_matches = analyser.theme_count(self._themes)
            proc_thread_warn(f'Number of matches is {no_matches}')

        except (IncompleteRead,HTTPError,URLError,RemoteDisconnected,timeout,CertificateError) as e:
            proc_thread_err(f'{e} while requesting a response from {focus_url}')
            return False

        except (UnicodeDecodeError,UnicodeEncodeError) as e:
            proc_thread_err(f'{e} while requesting a response from {focus_url}')
            return False

        if not no_matches >= self._match_threshold:
            proc_thread_info(f'Not enough matches in {focus_url}, continuing')
            return False

        return True

    def preprocess(self, URL: str, HTML: str, headers: dict) -> Tuple[str, str, dict]:
        """Prepare the gathered data to be yielded.
        """
        # TODO
        proc_thread_debug(f'Preprocessing an result')
        return tuple(URL, HTML, headers)
