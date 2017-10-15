#coding:utf-8
import time
import traceback


class DecoFuture():
    def __init__(self, logger):
        self.logger = logger

    def catch(self, flag):
        def dec(func):
            def wraped(*args, **kwargs):
                while 1:
                    back = None
                    try:
                        back = func(*args, **kwargs)
                    except Exception, e:
                        self.logger.error(str(e))
                        s = traceback.format_exc()
                        self.logger.error(str(s))
                    time.sleep(0.1)
                    if flag == "while":
                        pass
                    else:
                        break
                return back
            return wraped
        return dec
