#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from multiprocessing import current_process

logging.basicConfig(
    level=logging.DEBUG,
    filemode='w',
    format='%(processName)s %(threadName)s %(module)s %(levelname)s [%(asctime)s] [%(lineno)s] %(message)s.',
    datefmt="%M:%S")

# GENERAL
general_log = logging.getLogger(name=__name__)

# LOG crawled WEBSITES
crawl_log = logging.getLogger(name='crawled')
crawl_log_handler = logging.FileHandler('crawled.log')
crawl_log_handler.setFormatter(logging.Formatter('%(message)s.'))
crawl_log.addHandler(crawl_log_handler)


def proc_warn(message: str):
    general_log.warning(f'{current_process().name} {message}')


def proc_thread_warn(message: str):
    general_log.warning(f'{current_process().name} {current_thread().name} {message}')


def proc_err(message: str):
    general_log.error(f'{current_process().name} {message}')


def proc_thread_err(message: str):
    general_log.error(f'{current_process().name} {current_thread().name} {message}')


def proc_info(message: str):
    general_log.info(f'{current_process().name} {message}')


def proc_thread_info(message: str):
    general_log.info(f'{current_process().name} {current_thread().name} {message}')


def proc_debug(message: str):
    general_log.debug(f'{current_process().name} {message}')


def proc_thread_debug(message: str):
    general_log.debug(f'{current_process().name} {current_thread().name} {message}')


def proc_critical(message: str):
    general_log.critical(f'{current_process().name} {message}')


def proc_thread_critical(message: str):
    general_log.critical(f'{current_process().name} {current_thread().name} {message}')
