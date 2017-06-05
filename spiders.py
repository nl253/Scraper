#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# TODO
# 1. Export module
#   - output with
#           * SQLite3
#           * csv
#           * mysql
#           * JSON ?
#           * redis ?
#           * mongo ?
#
# 2. Expand the analysis module
#   - parsing with lxml, it's faster
#    (but use regex for simple tasks
#     because it's faster than both)
#
# 3. Testing
#   - make sure it works with
#       * 1 CPU (core)
#       * 1 thread
#       * prevent bad input (self._safe())
#       * use unittest


from abc import abstractmethod, ABCMeta
from copy import copy
from ctypes import c_int32
from http.client import RemoteDisconnected, IncompleteRead
from multiprocessing import Queue as SharedProcessQueue, cpu_count, Process
from multiprocessing.managers import ListProxy, DictProxy, SyncManager as ProcessSyncManager, Value as CValue
from signal import pthread_kill
from socket import timeout
from ssl import CertificateError
# Standard Library
from threading import Barrier, Thread, local as threadvars, Timer as ThreadTimer
from time import sleep
from typing import List, Iterable, Any, Optional
from urllib.error import HTTPError, URLError

from _test_spiders import BaseSpiderVerifier
# OWN
from analysis import HTMLAnalyser, HTMLWrapper
from logutils import *


class BaseSpider(metaclass=ABCMeta):
	"""Asynchronous, multithreading and multiprocessing iterable spider.
	This is a base class that will have many implementations.
	"""

	def __init__(self,
	             starting_urls: Iterable[str],
	             max_results: int = 1000,
	             timeout: int = 3000,
	             max_child_processes: int = 3,
	             max_threads: int = cpu_count()):

		# Settings
		self._max_threads: int = max_threads
		self._max_children: int = max_child_processes
		self._max_results: int = max_results
		self._timeout: int = timeout

		# Initialise
		self._manager: ProcessSyncManager = ProcessSyncManager()
		self._manager.start()

		# Efficiently store crawled data until yielded
		self._results: SharedProcessQueue = SharedProcessQueue(self._max_results)

		# Simulate collections.Counter
		self._URLs: DictProxy = self._manager.dict()

		# Keep track of how many have been yielded
		self._yielded_counter: CValue = self._manager.Value(c_int32, 0)

		# Initial URLs, prevent duplication
		for URL in set(starting_urls):
			self.add_URL(URL)

		# Store all processed to ensure each is visited once
		self._processed_URLs: ListProxy = self._manager.list()

		# Later, blocks the main threads from killing child-threads
		# until they signal
		self._child_end_barrier = Barrier(max_child_processes)

	@property
	def yielded(self) -> int:
		"""The count of items yielded so far. DO NOT OVERRIDE.
		"""
		return self._yielded_counter.value

	@property
	def max_children(self) -> int:
		"""Max child processes (a cap).
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
		"""Max threads spawned by each child-process (a cap).
		"""
		return self._max_threads

	@max_threads.setter
	def max_threads(self, new_value):
		self._max_threads = new_value

	@property
	def timeout(self) -> float:
		"""When timeout passes the spider will stop crawling.
		"""
		return self._timeout

	@timeout.setter
	def timeout(self, new_timeout):
		self._timeout = new_timeout

	@staticmethod
	@abstractmethod
	def preprocess(self, URL: str, HTML: str, headers: dict) -> Any:
		"""Apply to each result, needs to have this exact method signature,
		it aims to prepare the gathered data to be yielded.
		NEEDS TO BE OVERRIDDEN.
		"""
		proc_thread_debug(f'Preprocessing an result')
		return tuple([URL, HTML, headers])

	def add_result(self, URL: str, HTML: str, headers: dict):
		"""Used by child processes to add gathered entries into temp storage
		(self._results: SharedProcessQueue).
		The data is passed on to preprocess before adding an result.
		YOU DO NOT CALL THIS DIRECTLY.
		"""
		self._results.put(BaseSpider.preprocess(URL, HTML, headers))
		proc_thread_debug(f'Added an result, Entries atm: {self._results.qsize()}')

	@abstractmethod
	def produce(self) -> Optional[Any]:
		"""Applies to every result AFTER preprocesing and AFTER it has
		been places on queue of ready-results.
		May be used to export to a database, or printed to STDOUT.
		NEEDS TO BE OVERRIDDEN.
		"""
		return self._results.get()

	@property
	def processed_URLs(self) -> List[str]:
		"""A list of processed URLs that have been visited and
		results from them have been added or have been visited but
		didn't pass the test_result() test. Basically ALL.
		"""
		return list(copy(self._processed_URLs))

	def crawl(self):
		"""The method to be called directly by the user, all others are helper-methods.
		CALL DIRECTLY BUT DO NOT OVERRIDE.
		"""

		# keep track of active processes to kill later
		children: List[Process] = [
			Process(target=self._child_spawn, name=f"Process {i}") \
			for i in range(self._max_children)]

		for child in children:
			proc_thread_warn(f'Starting {child.name}')
			child.start()
			sleep(2)

		# loop while enough results haven't been yielded
		while self._yielded_counter.value < self._max_results:
			# if something to yield
			if self._results.qsize() > 0:
				while not self._results.empty():
					self._yielded_counter.value += 1
					yield self.produce()
			# elif all child-processes (and their threads) are dead
			elif all(map(lambda child: not child.is_alive(), children)):
				break
			else:
				# report
				# check every 8 seconds
				proc_thread_warn(f'{self._yielded_counter.value} / {self._max_results}')
				sleep(8)

		# on break
		self._kill_children(children)
		proc_thread_warn(f'Scraping finished, all children dead')

	def _kill_children(self, children):
		"""Kill remaining children, must be done here, in the main thread
		(because it spawned them)"""
		proc_thread_warn(f'Killing children')

		# when done
		for child in filter(lambda child: not child.is_alive(), children):
			proc_thread_warn(f'Killing child {child.name}')
			sleep(2)
			child.terminate()

	@property
	def URLs(self) -> Iterable[str]:
		"""List of URLs that are 'enqueued' and will be processed.
		"""
		return self._URLs.keys()

	def add_URL(self, URL: str):
		"""YOU DO NOT call this directly, all it does is
		simulate collections.Counter behaviour when adding a
		URL to List of URLs to be scraped.
		Like collections.Counter it will assign a value to each
		URL which is a key, if this URL has been stored, the value (int) is
		incremented, else a new entry is made with a value of 1 and
		key being the URL.
		It is very inefficient but ensures that
		relevant websites are visited.
		"""
		if len(URL) > 0:
			for stored_URL in self._URLs:
				if stored_URL == URL:
					self._URLs[stored_URL] += 1
					return True
			self._URLs[URL] = 1
			return True
		else:
			return False

	@property
	def next_URL(self) -> str:
		"""Retrieve the next URL and remove it from the list of
		URLs to be scraped.
		"""
		assert len(self._URLs) > 0, 'No more URLs to get!'
		most_freq = max(self._URLs.values())
		for URL in self._URLs:
			if self._URLs[URL] == most_freq:
				self._processed_URLs.append(URL)
				del (self._URLs[URL])
				proc_thread_warn(
					f'Appending {URL} to _processed_URLs which accumulated {len(self._processed_URLs)} items')
				return URL

	def _thread_start(self):
		"""Called by each child process on each of it's threads.
		This is what generates the actual HTML documents
		and links and adds them to lists and queues. This is the core
		of each Spider. Looping takes place while enough entries
		have not been generated. Note that these
		threads will be killed by the
		main thread anyway if the timout has passed.
		Also, if they repetedly try to get something off an
		empty queue, they will be killed (they break and signal to the main
		thread to break the barrier which kills all
		threads in a child-process)
		"""

		# keep track of how many times this thread failed to get next URL
		threadvars.misses = 0

		def report():
			proc_thread_warn(
				f'Yielded {self._yielded_counter.value} / {self._max_results}')

			proc_thread_warn(
				f'Produced {self._yielded_counter.value + self._results.qsize()} results out of / {self._max_results}')

			proc_thread_warn(
				f'{self._results.qsize()} items waiting to be yielded')

			# fetch next
			proc_thread_warn(
				f'Attempting to get another link off the Counter')

		while self._yielded_counter.value + self._results.qsize() <= self._max_results:

			report()  # info after each loop

			# if no more links even after 5 tries - break
			try:
				focus_url = self.next_URL
				threadvars.misses = 0  # reset

				proc_thread_warn(
					f'Focus URL: {focus_url} taken off URLs which has {len(self.URLs)} items left')

			except AssertionError:
				# this assertion checks for len(links to scrape)
				threadvars.misses += 1
				# 5 times tried to get from queue with no effect, finish thread
				if threadvars.misses > 5:
					proc_thread_warn(
						f'more than 5 failures to get from self._url_queue. Breaking')
					break
				else:
					sleep(5)
					continue

			try:
				# instantiate an HTMLWrapper object
				proc_thread_warn(f'Trying to request from {focus_url}')
				wrapper = HTMLWrapper(focus_url)

			except (IncompleteRead, HTTPError, URLError,
			        RemoteDisconnected, timeout, CertificateError) as e:
				proc_thread_err(f'{e} while requesting from {focus_url}')
				continue

			except (UnicodeDecodeError, UnicodeEncodeError) as e:
				proc_thread_err(f'{e} while requesting from {focus_url}')
				continue

			if not self._results.full():
				if self.test_result(wrapper.URL, wrapper.HTML, wrapper.headers):
					self.add_result(focus_url, wrapper.HTML, wrapper.headers)
					for URL in wrapper.iURLs:
						self.add_URL(URL)
			else:  # if results are full (as specified in constructor)
				proc_thread_warn(f'Enough entries gathered')
				break

		# on break
		proc_thread_warn(f'Enough entries gathered')
		# signal to the main thread, if all threads in a child-process
		# terminate like this, then the main thread will end
		# this child-process
		return self._child_end_barrier.wait(timeout=10)

	def _safe(self) -> bool:
		"""Used to check if it's OK to begin crawling when crawl()
		is called. For safety.
		"""
		# TODO
		return BaseSpiderVerifier(self).sane()

	def _child_spawn(self):
		"""To be run by the main theread of the main process on
		each of created Process instances.
		At the end the semaphore is released.
		"""

		# acquire by the main thread on every child-process on start()

		proc_thread_warn(f'Creating threads')

		threads = [
			Thread(target=self._thread_start, name=f"Thread {i}") \
			for i in range(self._max_threads)]

		proc_thread_warn(f'Threads: {threads}')

		for thread in threads:
			proc_thread_warn(f'Starting thread: {thread.name}')
			# delay between spawning, needed for synchronization
			sleep(1)
			thread.start()

		timer = ThreadTimer(self._timeout, self._child_end)
		timer.start()

		# wait for all spawned threads to notify on break
		self._child_end_barrier.wait(timeout=self._timeout)

		# call clean-up method
		return self._child_end(threads)

	def _child_end(self, threads: List[Thread]):
		"""Called by the main thread, kills all spawned
		threads, realeases the semaphore acquired on child creation
		 and cleans up.
		"""
		for thread in threads:
			proc_thread_warn(
				f'Enough data produced, killing threads')
			sleep(2)  # delay
			pthread_kill(thread.ident)

		proc_thread_warn('crawler is relasing a semaphore')

		return True

	@abstractmethod
	def test_result(self, URL: str, HTML: str, headers: dict) -> bool:
		"""To be overriden by a boolean-return function that takes these exact args.
		This is repetedly applies to all scraped results and determines if
		links from that website should be added to `to be scraped` as well
		as if the website itself ie the html doc will be added as an entry.
		"""
		pass


class ThemeSpider(BaseSpider):
	"""An implementation of BaseSpider that hunts for themes passed as List[str].
	It will output results as chunks of texts relevant to the themes passed
	to the constructor.
	"""

	def __init__(self, starting_urls: Iterable[str],
	             themes: List[str],
	             max_results: int = 1000,
	             timeout: int = 3000,
	             match_threshold=12,
	             max_child_processes: int = 3,
	             max_threads: int = cpu_count()):

		super().__init__(
			starting_urls,
			max_results,
			timeout,
			max_child_processes,
			max_threads)

		# ADDED ON TOP OF WHAT WAS IN BaseSpider
		# hunt for these themes in HTML documents
		self._themes: Iterable[str] = themes

		# min matches on a page to add entries and links
		self._match_threshold: int = match_threshold

	def test_result(self, URL: str, HTML: str, headers: dict) -> bool:

		try:
			# instantiate an analyser object
			proc_thread_warn(f'Making an HTMLAnalyser')
			analyser = HTMLAnalyser(URL)

			# count matches on the focus page
			no_matches = analyser.theme_count(self._themes)
			proc_thread_warn(f'Number of matches is {no_matches}')

		except (IncompleteRead, HTTPError, URLError,
		        RemoteDisconnected, timeout, CertificateError) as e:
			proc_thread_err(
				f'{e} while requesting a response from {analyser.URL}')
			return False

		except (UnicodeDecodeError, UnicodeEncodeError) as e:
			proc_thread_err(
				f'{e} while requesting a response from {analyser.URL}')
			return False

		if not no_matches >= self._match_threshold:
			proc_thread_info(
				f'Not enough matches in {analyser.URL}, continuing')
			return False

		return True

	def preprocess(self, URL: str, HTML: str, headers: dict) -> Any:
		"""Prepare the gathered data to be yielded.
		"""
		# TODO
		proc_thread_debug(f'Preprocessing an result')
		return tuple([URL, HTML, headers])
