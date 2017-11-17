#!/usr/bin/env python
# -*- coding:utf-8 -*-

import re
import time
import setproctitle
import simplejson
import signal

from lib.log import logger
from lib.daemon import daemonize
from lib.utils import external_cmd
from lib.networkinfo import get_ip_info
from conf.config import DAEMON_MODE, PROC_NAME, DETECT_LIST, SLEEP_INTERVAL, TABLES
from conf.config import EXCEPT_BODY, SWITCH_BODY, PING_THOLD
from lib.mail import MailHandler
from lib.exception import LoseDefaultGateway, ExecException
from lib.fetchman import HttpClient

global is_running
is_running = True

def sig_handler(num, stack):
    logger.info('receiving signal, exiting...')
    global is_running
    is_running = False

def get_defualt_route(ip_map):
    """
    :return: 如果文件获取失败,或者任何key不匹配都是异常
    """
    route_file = "/route.sh"
    try:
        fd = open(route_file, "r")
        file_str = fd.read()

        cnc_gateway = re.findall("\sCNC_GATEWAY=(\d+\.\d+\.\d+\.\d+)", file_str)[0]
        cnc_device = re.findall("\sCNC_DEVICE=(\w+\.\w+)\s", file_str)[0]

        ctl_gateway = re.findall("\sCTL_GATEWAY=(\d+\.\d+\.\d+\.\d+)", file_str)[0]
        ctl_device = re.findall("\sCTL_DEVICE=(\w+\.\w+)\s", file_str)[0]

        cmb_gateway = re.findall("\sCMB_GATEWAY=(\d+\.\d+\.\d+\.\d+)", file_str)[0]
        cmb_device = re.findall("\sCMB_DEVICE=(\w+\.\w+)\s", file_str)[0]

    except:
        msg = "route file is not exist or format is error"
        logger.error(msg)
        send_except_mail(msg, ip_map)
        exit(1)

    table_res = {
        "100": {
            "gateway": cnc_gateway,
            "device": cnc_device,
        },
        "200": {
            "gateway": ctl_gateway,
            "device": ctl_device,
        },
        "210": {
            "gateway": cmb_gateway,
            "device": cmb_device,
        }
    }
    gate_map = {
        cnc_gateway: cnc_device,
        ctl_gateway: ctl_device,
        cmb_gateway: cmb_device
    }
    return table_res, gate_map


def check_ip_map(ip_map):
    if len(ip_map)is not 3:
        msg = "不是三线机器，程序将要推出..."
        logger.error(msg)
        send_except_mail(msg, ip_map)
        exit(1)


def check_ping(cmd):
    """
    :return
        success_nums int: success
        ping_cost    int: time cost
    """
    p, stdout, stderr = external_cmd(cmd)
    if stdout is None:
        return 0, 0

    success_nums = len(re.findall("64 bytes from\s", stdout))
    ping_cost_str = re.findall("\stime=(\d*)", stdout)
    ping_cost = sum([int(i) for i in ping_cost_str])

    return success_nums, ping_cost


def parse_ping_result(ip_map):
    """
    :return:eg
    {
        "100" : [10, 140],
        "210" : [10,140],
        "200" : [10,140]
    }
    """
    cmd_format = "ping -i 0.2 -w 2 -c 10 -I {bind_ip} {detect_ip}"
    detect_dict = {}
    for bind_ip, table in ip_map.items():
        for _d_ip in DETECT_LIST:
            success_tmp, cost_tmp = check_ping(cmd_format.format(bind_ip=bind_ip, detect_ip=_d_ip))
            success_nums = success_nums + success_tmp
            ping_cost = ping_cost + cost_tmp
        detect_dict[table] = [success_nums, ping_cost]
    return detect_dict


def send_except_mail(msg, ip_map):
    mail = MailHandler()
    title = "网络探测服务异常"
    content = EXCEPT_BODY.format(ip_map=ip_map, msg=msg)
    mail.send_mail(title, content)


def send_switch_mail(del_cmd, add_cmd, detect_dict, current_gateway, current_dev, table, ip_map):
    mail = MailHandler()
    title = "默认路由切换"
    content = SWITCH_BODY.format(ip_map=ip_map, del_cmd=del_cmd, add_cmd=add_cmd,
                                 detect_dict=simplejson.dumps(detect_dict, indent=2),
                                 current_gateway=current_gateway, current_dev=current_dev, table=table)
    mail.send_mail(title, content)


class Deroute(object):

    def __init__(self, ip_map):
        self.ip_map = ip_map
        self.default_route, self.gate_map = get_defualt_route(ip_map)


    def execute(self):
        """
        每轮循环前，检查路由表,是否table有网关,防止手动修改路由表导致获取不到默认网关
        出现异常退出的时候，检查是否三表都有路由
        """
        global is_running

        while is_running:
            try:
                self.check_three_table()
                self.avoid_lose()
                self.check_ip_gateway()
                self._execute()
            except Exception as e:
                self.avoid_lose()
                err_msg = str(e)
                logger.error(err_msg)
                send_except_mail(err_msg, self.ip_map)
                self.exit_check()

            time.sleep(SLEEP_INTERVAL)

    def avoid_lose(self):
        res = self.check_current_gateway()
        logger.info("check three table gateway ,res is %s" % res)
        if res is False:
            logger.info("find three table gateway is all not default gateway ,will restore default gateway")
            self.restore_default_gateway()

    def check_current_gateway(self):
        count = 0
        for table in TABLES["check_table"]:
            current_gateway = self.get_current_gateway(table)[0]
            default_gateway = self.default_route[table]["gateway"]
            if current_gateway != default_gateway:
                count += 1
        if count ==3:
            return False
        return True

    def restore_default_gateway(self):
        for table in TABLES["check_table"]:
            gate_ip = self.default_route[table]["gateway"]
            gate_dev = self.default_route[table]["gateway"]
            self.add_route(gate_ip, gate_dev, table)


    def add_route(self, ip, dev, table):
        cmd = "ip route add default via %s dev %s table %s" % (ip, dev, table)
        p, stdout, stderr = external_cmd(cmd)
        logger.info("will execute the cmd %s" % cmd)
        if p.returncode != 0:
            return False
        return True

    def add_rule(self, from_ip, to_ip, table):
        cmd = "ip rule add from %s to %s table %s pref 2500" % (from_ip, to_ip, table)
        p, stdout, stderr = external_cmd(cmd)
        if p.returncode != 0:
            return False
        return True

    def check_ip_gateway(self):  # 三线ip 的三条路由检查
        '''
            1，检查三线ip 是否有默认网关
            2，检查detect_list 和 jump_list 是否有rule
            以上如果没有默认都将添加
            '''
        for ip, table in self.ip_map.items():
            if table == "100":
                map_table = "111"
            elif table == "200":
                map_table = "112"
            else:
                map_table = "113"

            cmd = "ip route show table %s" % map_table
            p, stdout, stderr = external_cmd(cmd)
            if stdout == "" or stdout is None:
                gate_ip = self.default_route[table]["gateway"]
                gate_dev = self.default_route[table]["device"]
                res = self.add_route(gate_ip, gate_dev, map_table)
                logger.info("check and ip add route ,execute %s" % cmd)
                if res == False:
                    msg = "three for ip table add default gateway failed "
                    send_except_mail(msg, self.ip_map)
                    logger.error(msg)
                    exit(1)

            for to_ip in DETECT_LIST:
                rule_cmd = "ip rule show |grep %s |grep %s" % (to_ip, map_table)
                rule_p, rule_stdout, rule_stderr = external_cmd(rule_cmd)
                if rule_stdout == "" or rule_stdout is None:
                    res = self.add_rule(ip, to_ip, map_table)
                    logger.info("check and ip add rule ,execute %s" % rule_cmd)
                    if res == False:
                        msg = "three for ip rule add default gateway failed "
                        send_except_mail(msg, self.ip_map)
                        logger.error(msg)
                        exit(1)

    def exit_check(self):
        for table in TABLES["check_table"]:
            cmd = "ip route show table %s" % table
            p, stdout, stderr = external_cmd(cmd)
            if stdout == "" or stdout is None:
                default_gateway = self.default_route[table]["gateway"]
                default_dev = self.default_route[table]["device"]
                add_cmd = "ip route add default via %s dev %s table %s" % (default_gateway, default_dev, table)
                p, stdout, stderr = external_cmd(add_cmd)
                if p.returncode == 0:
                    logger.info("table %s restore the defualt gateway %s" % (table, default_gateway))
            else:
                logger.info("table %s has gateway ,will exit")

    def _execute(self):
        '''
        如果没有三线ip,立刻抛出异常
        丢包率大于阀值，走的默认路由，改到最好网关
        丢包率大于阀值，走的非默认路由，table默认网关不通
        丢包率正常后，走的非默认路由，恢复默认线路
        '''
        self.detect_dict = parse_ping_result(self.ip_map)
        self.best_gateway = self.get_best_gateway(self.detect_dict)

        for table, cost_list in self.detect_dict.items():
            default_gateway = self.default_route[table]["gateway"]
            current_gateway, current_dev = self.get_current_gateway(table)
            lose_per = float('%.4f' % (float(len(DETECT_LIST) * 10 - cost_list[0]) / (len(DETECT_LIST) * 10) * 100))

            if lose_per >= PING_THOLD and current_gateway == default_gateway:
                logger.info("table %s ,lose package percent: %s has bigger than thold ,current_gateway "
                            "%s will switch %s ", table, lose_per, current_gateway, self.best_gateway)
                if current_gateway != self.best_gateway:
                    self.switch_gateway(self.best_gateway, current_gateway, table, current_gateway, current_dev)
                else:
                    logger.info("table %s ,current gateway is the best gateway" % table)

            elif lose_per >= PING_THOLD and current_gateway != default_gateway:
                logger.info("table %s default_gateway is %s ,current_gateway is %s  ping not ok",
                            table, default_gateway, current_gateway)

            elif lose_per < PING_THOLD and current_gateway != default_gateway:
                logger.info("table %s ,current gateway is :%s ,will switch to default gateway %s ,ping ok",
                            table, current_gateway, default_gateway)
                self.switch_gateway(default_gateway, current_gateway, table, current_gateway, current_dev)

            else:
                logger.info("table %s , curremt_gateway is %s  default_gateway %s , ping is ok",
                            table, current_gateway, default_gateway)

    def switch_gateway(self, dst_gateway, src_gateway, table, current_gateway, current_dev):
        src_dev = self.gate_map[src_gateway]
        dst_dev = self.gate_map[dst_gateway]

        del_cmd = "ip route del default via %s dev %s table %s" % (src_gateway, src_dev, table)
        p, stdout, stderr = external_cmd(del_cmd)
        logger.info("del route :%s, stdout is:%s , stderr is:%s" % (del_cmd, stdout, stderr))
        if p.returncode != 0:
            raise Exception(stderr)

        add_cmd = "ip route add default via %s dev %s table %s" % (dst_gateway, dst_dev, table)
        p, stdout, stderr = external_cmd(add_cmd)
        logger.info("add route :%s, stdout is:%s , stderr is:%s" % (add_cmd, stdout, stderr))
        if p.returncode != 0:
            raise Exception(stderr)

        send_switch_mail(del_cmd, add_cmd, self.detect_dict, current_gateway, current_dev, table, self.ip_map)

    def get_best_gateway(self, detect_dict):
        success_sort = sorted(detect_dict.iteritems(), key=lambda d: d[1][0], reverse=True)
        time_sort = sorted(detect_dict.iteritems(), key=lambda d: d[1][1], reverse=False)

        if success_sort[0][0] is not time_sort[0][0]:
            min_table = success_sort[0][0]
        else:
            min_table = time_sort[0][0]

        return self.default_route[min_table]["gateway"]

    def get_current_gateway(self, table):
        cmd = "ip route show table %s" % table
        p, stdout, stderr = external_cmd(cmd)
        if p.returncode != 0:
            raise ExecException("get default table gateway failed")

        gateway = re.findall("default via\s(\d+\.\d+\.\d+\.\d+)\s", stdout)
        dev = re.findall("default via\s\d+\.\d+\.\d+\.\d+\sdev\s(\w+)", stdout)

        return gateway[0], dev[0]

    def check_three_table(self):
        for table in TABLES["check_table"]:
            cmd = "ip route show table %s" % table
            p, stdout, stderr = external_cmd(cmd)
            if stdout == "" or stdout is None:
                raise LoseDefaultGateway("table lose gateway ,will exit...")


def init():
    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)
    signal.siginterrupt(signal.SIGINT, False)
    signal.siginterrupt(signal.SIGTERM, False)

    ip_map = get_ip_info()
    check_ip_map(ip_map)  # 非三线ip ,立刻抛出异常

    setproctitle.setproctitle(PROC_NAME)

    if DAEMON_MODE:
        daemonize()
    logger.info("deroute")

    d = Deroute(ip_map)
    d.execute()


if __name__ == "__main__":
    logger.info('engine start')
    init()

