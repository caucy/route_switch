# coding:utf-8
import logging
from logging import Logger

import commands
import simplejson
from datetime import datetime

from conf.config import LOG_PATH, LOG_ERROR_FILE, LOG_FILE, IS_SYSLOG


default_level = logging.INFO
_, hostname = commands.getstatusoutput("hostname -s")


def get_logger(logfile, level=None, mark=None):
    if mark in Logger.manager.loggerDict:
        return logging.getLogger(mark)

    logfile = LOG_PATH + logfile
    if mark:
        _logger = logging.getLogger(mark)
    else:
        _logger = logging.getLogger('root')

    if not level:
        level = logging.INFO

    _logger.setLevel(level)

    fmt = '%(asctime)s - %(name)s - %(process)s - %(levelname)s: - ' \
          'func:%(filename)s.%(funcName)s.%(lineno)dn - %(message)s'

    formatter = logging.Formatter(fmt, datefmt='%Y-%m-%d,%H:%M:%S')
    handler = logging.FileHandler(logfile)
    handler.setFormatter(formatter)
    _logger.addHandler(handler)

    logfile = LOG_PATH + LOG_ERROR_FILE
    file_handler = logging.FileHandler(logfile)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.ERROR)
    _logger.addHandler(file_handler)

    if IS_SYSLOG:
        from logging.handlers import SysLogHandler
        sysl = SysLogHandler(address='/dev/log', facility=SysLogHandler.LOG_USER)
        sysl.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
        _logger.addHandler(sysl)
        _logger.setLevel(logging.INFO)

    return _logger


def log_stdout(task_id, msg=''):
    log = {
        "datetime": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "task_id": str(task_id),
        "log_level": "error",
        "hostname": hostname,
        "description": msg
    }
    return simplejson.dumps(log)


logger = get_logger(LOG_FILE, level=logging.INFO, mark='init')


if __name__ == "__main__":
    pass
