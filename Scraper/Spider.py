#!/usr/bin/env python3
# coding: utf-8

if __name__ != '__main__':
    print("[ERROR] must be run as a script!")
    import sys

    sys.exit(0)

# Standard Library
import concurrent.futures
import logging
import queue
import re
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from logging import Logger
from time import sleep, time
from typing import Callable, Iterable, List, Set, Tuple

#  import lxml.html

logging.basicConfig(
        level=logging.DEBUG,
        filemode='w',
        format=
        '%(processName)s %(threadName)s %(module)s %(levelname)s [%(asctime)s] [%(lineno)s] %(message)s.',
        datefmt="%M:%S"
)

log: Logger = logging.getLogger(name=__name__)


def resolve(url: str, current_url: str) -> str:
    """
    Resolve relative URLs.

    :param url: relative url you want to resolve (atm it doesn't deal with `../`)
    :param current_url: current url
    :return: str
    """
    if 'http' in url:
        return url

    parsed = list(urllib.parse.urlparse(url, allow_fragments=False))
    parsed_current = urllib.parse.urlparse(current_url, allow_fragments=False)
    for i in range(3):
        if not parsed[i]:
            parsed[i] = parsed_current[i]

    return urllib.parse.urlunparse(parsed)


def crawl(url: str) -> Iterable[str]:
    """
    Return a list of URLs from a URL.

    Links are extracted from anchor tags, href attribute.

    I have commented out lxml bits because for this base spider lxml is not
    necessary, although it makes sense to use it in any other case.

    :param url: URL you want to extract links from
    :return: an iterable of urls
    """
    try:
        with urllib.request.urlopen(url, timeout=5) as instream:
            with concurrent.futures.ThreadPoolExecutor(8) as pool:
                #  DOM: lxml.html.etree.ElementTree = pool.submit(lxml.html.fromstring,
                #  h).result(7)

                return (i for i in pool.map(lambda x: x.group('url'),
                                            pool.submit(re.compile(
                                                    r'href="(?P<url>.*?)"').finditer,
                                                        pool.submit((
                                                                        pool.submit(
                                                                                instream.read).result(
                                                                                7)).decode,
                                                                    'utf-8').result(
                                                                7)).result()) if
                        not re.compile(
                                r'\.(?P<extension>css|js|(min|slim).\w+)').search(
                                i))

                #  return pool.map(lambda x: x.attrib['href'],
                #  pool.submit(DOM.cssselect, "a[href]").result(7), chunksize=10)

    except Exception as e:
        log.warning(f"failed to obtained results from {url}\n {e}")
        return []


# noinspection PyIncorrectDocstring
def main(starting_urls: List[str], _waited=False, timeout=30,
         _start=time(), _results=queue.LifoQueue(), _scraped=set(),
         _jobs=queue.Queue()):
    """
    The main method.

    Recursion is used here to terminate.

    :param starting_urls: List of starting urls
    :param timeout: timeout in seconds

    """
    for i in starting_urls: _jobs.put(i)

    with ThreadPoolExecutor(16) as pool:
        while not _jobs.empty():  # queue
            if (time() - _start) >= timeout: break
            job: str = _jobs.get()  # url
            result: Iterable[str] = pool.submit(crawl, job).result()
            if result:  # might return an empty list (which evaluates to False)
                log.info(f"obtained results from {job}")
                # map results to abs URLs
                for i in (resolve(i, job) for i in result):
                    # don't scrape the same websites more than 1
                    if i not in _scraped:
                        log.info(f"unique result: {i}, adding")
                        _results.put(i)
                        if re.compile(r'http').search(i):  # ensure valid URL
                            log.warning(f'adding a crawl job {i}')
                            _jobs.put(i)  # before adding a crawl job
                        else:
                            log.warning(f"rejecting {i}")
                    else:
                        log.info(f"{i} already scraped")
            sleep(1)

    if _waited or (time() - _start) < timeout:  # END OF FUNCTION
        # any postprocessing of results should take place here
        while not _results.empty():
            log.info(_results.get())
    else:
        return main(_waited=True, starting_urls=[], _start=_start,
                    timeout=timeout, _results=_results, _scraped=_scraped,
                    _jobs=_jobs)


main(starting_urls=[
            "https://www.google.co.uk/search?q=multithreading&ie=utf-8&oe=utf-8&client=firefox-b-ab&gfe_rd=cr&dcr=0&ei=raH3Wcj3IcWh4gSFi5DYBg",
            "https://www.tutorialspoint.com/operating_system/os_multi_threading.htm",
            "https://en.wikipedia.org/wiki/Translation_lookaside_buffer",
            "https://en.wikipedia.org/wiki/Content-addressable_memory",
            "https://docs.scipy.org/doc/numpy-dev/user/basics.indexing.html",
            "https://docs.scipy.org/doc/numpy-dev/reference/ufuncs.html"
        ],
        timeout=500
)
