# encoding=utf8
import subprocess
import re
import platform
import time

from IPy import IP
from lib.fetchman import HttpClient
from lib.log import logger

http_man = HttpClient(logger)


def find_all_ip(plat=None):
    if plat is None:
        plat = platform.system()

    ipstr = '([0-9]{1,3}\.){3}[0-9]{1,3}'
    if plat == "Darwin" or plat == "Linux":
        ipconfig_process = subprocess.Popen("ifconfig", stdout=subprocess.PIPE)
        output = ipconfig_process.stdout.read()
        ip_pattern = re.compile('(inet %s)' % ipstr)
        if plat == "Linux":
            ip_pattern = re.compile('(inet addr:%s)' % ipstr)
        pattern = re.compile(ipstr)
        iplist = []
        for ipaddr in re.finditer(ip_pattern, str(output)):
            ip = pattern.search(ipaddr.group())
            if ip.group() != "127.0.0.1":
                iplist.append(ip.group())
        return iplist
    elif plat == "Windows":
        ipconfig_process = subprocess.Popen("ipconfig", stdout=subprocess.PIPE)
        output = ipconfig_process.stdout.read()
        ip_pattern = re.compile("IPv4 Address(\. )*: %s" % ipstr)
        pattern = re.compile(ipstr)
        iplist = []
        for ipaddr in re.finditer(ip_pattern, str(output)):
            ip = pattern.search(ipaddr.group())
            if ip.group() != "127.0.0.1":
                iplist.append(ip.group())
        return iplist


def req_ip_info(ip):
    isp_dict = {
        u"电信": "200",
        u"移动": "210",
        u'联通': "100"
    }
    url = "http://ip.taobao.com//service/getIpInfo.php"
    while 1:
        res = http_man.safe_fetch(url, method='post', body={'ip': ip})
        if res:
            return isp_dict[res['data']['isp']]
        time.sleep(1)


def get_ip_info():
    """
    :return:
    {
    101.71.76.1 : 100
    183.131.54.129 : 200
    120.199.83.1 : 210
    }
    """
    ip_list = find_all_ip()
    res = {}
    for ip in ip_list:
        item = IP(ip)
        if item.iptype() == 'PUBLIC':
            isp = req_ip_info(ip)
            res[ip] = isp
    return res


if __name__ == "__main__":
    system = platform.system()
    print(find_all_ip(system))
