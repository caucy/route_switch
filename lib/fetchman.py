#!/usr/bin/env python
# -*- coding:utf-8 -*-

import socket
import logging
import traceback

import requests
import simplejson

from lib.log import logger
from conf.config import ENGINE_REQUEST_TIMEOUT


logging.getLogger("requests").setLevel(logging.WARNING)


class HttpClient(object):
    def __init__(self, logger_obj=None):
        if logger_obj is None:
            logger_obj = logger

        self.logger = logger_obj

    def fetch(self, url, method='get', params=None, body=None, try_times=1):
        if not url.startswith("http://"):
            url = "http://" + url

        res = None
        status = False
        user_agent = {'User-Agent': "engine"}

        for i in xrange(1, try_times+1):
            try:
                res = requests.request(method, url, params=params, data=body, headers=user_agent,
                                       timeout=ENGINE_REQUEST_TIMEOUT)
            except requests.exceptions.Timeout:
                self.logger.error("fetch faild !!! url:%s connect timeout", url)
            except requests.exceptions.TooManyRedirects:
                self.logger.error("fetch faild !!! url:%s redirect more than 3 times", url)
            except requests.exceptions.ConnectionError:
                self.logger.error("fetch faild !!! url:%s connect error", url)
            except socket.timeout:
                self.logger.error("fetch faild !!! url:%s recv timetout", url)
            except:
                self.logger.error("fetch faild !!! url:%s %s" % (url, traceback.format_exc()))

        if res and res.status_code in [200, 201]:
            status = True
            self.logger.info("fetch success code: %s , url: %s" % (res.status_code, url))

        return res, status

    def safe_fetch(self, url, method='get', params=None, body=None, is_json=True):
        res, status = self.fetch(url, method, body=body, params=params)
        try:
            if status and is_json:
                return simplejson.loads(res.content)
            elif status and not is_json:
                return res

        except:
            self.logger.error("url: %s, reason: not json", url)

        return None


if __name__ == "__main__":
    pass
