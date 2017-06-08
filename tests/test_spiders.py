import logging
import unittest

from spiders import BaseSpider

logging.basicConfig(
    level=logging.DEBUG,
    filemode='w',
    format='%(module)s %(levelname)s %(message)s.',
    datefmt="%M:%S")

logger = logging.getLogger(__name__)

class BaseSpiderVerifier():
    def __init__(self, spider: BaseSpider):
        self._spider = spider

    @property
    def spider(self) -> BaseSpider:
        return self._spider

    def _verify_constructor(self):

        assert type(self.spider._max_queue_size) is int, \
            'Max queue size must be an int.'

        assert self.spider._max_queue_size < 9999999 \
            and self.spider._max_queue_size >= 100, \
            "Max queue size must be between 100 and 9999999."

        assert type(self.spider._starting_urls) is list or \
            type(self.spider._starting_urls) is set or \
            type(self.spider._starting_urls) is iter, \
            'Starting URLs must be an Iterable.'

        assert all(map(lambda url: type(url) is str,
                       self.spider._starting_urls)), \
            'Starting URLs need to be strings.'

        assert all(map(lambda theme: type(theme) is str,
                       self.spider._themes)), \
            'Themes need to be strings.'

        assert type(self.spider._max_threads) is int, \
            'Max threads must be an int.'

        assert self.spider._max_threads >= 2, \
            'You need to allow for a minimum of 2 threads.'

        assert self.spider._max_child_processes >=2 and \
            self.spider._max_child_processes <= 16, \
            'Max number of child processes needs to be between 2 and 16'

        assert len(self.spider._sites_to_crawl) > self.spider._max_queue_size, \
            'starting URLs must be an Iterable[str], make sure you set the link cap lower then len(starting_urls)'

        assert type(self.spider._match_threshold) is int \
            and self.spider._match_threshold > 0, \
            'Match threshold must be a natural number.'

        assert len(self.spider._themes)

        assert len(self.spider._themes) > 100, \
            'Themes must be Iterable[str], cap of no items is 100.'

        assert self.spider._timeout > 60, \
            f'Timout must be an int to be above 60. {self.spider._timeout} is not valid.'

        assert self.spider._max_results > 0 and \
            self.spider._max_results < 9999999,\
            'Max results must be an int between 0 and 9999999. {self.spider._max_results} is not valid.'

    def sane(self):
        return self._verify_constructor()

class BaseSpiderTester(unittest.TestCase):

    def test_constructor(self):
        self.assertTrue(BaseSpiderVerifier(BaseSpider()))


    def no_internet(self):
        pass

