# encoding=utf8

DAEMON_MODE = False#是否守护进程模式启动

PROC_NAME = "route"#进程名

LOG_PATH = "/var/log/"
LOG_FILE = "route.log"
LOG_ERROR_FILE = "route.error.log"
IS_SYSLOG = False

ENGINE_REQUEST_TIMEOUT = 32

SLEEP_INTERVAL = 5

PING_THOLD = 50 #丢包率阀值

PING_TIME_INTERVER = 0.2 #ping 间隔
PING_COUNT = 10 # ping 总数

DETECT_LIST = ["114.114.114.114"] #目标ip

TABLES ={
    "check_table": ["100", "200", "210"],#受控制列表
    "detect_table": ["111", "112", "113"] #三个ip的单独出口列表
}

#邮件配置
mail_conf = {
    "host": "mail.sinobbd.com",#邮件域名
    "sender": "网络探测",
    "username": "username",
    "passwd": "passed",
    "mail_postfix": "mail.com.example",
    "recipients": [
        "example.@qq.com",#收件人列表
        
    ]
}


#邮件模版
EXCEPT_BODY = """
<h3>三线主机: {ip_map} 异常</h3>

<pre>
100　表示　电信  ctcc
200　表示　联通  cucc
210  表示　移动  cmcc
</pre>

<pre>
异常信息为：
{msg}
</pre>

"""

SWITCH_BODY = """
<h3>三线主机: {ip_map} 即将切换</h3>

<pre>
100　表示　电信  ctcc
200　表示　联通  cucc
210  表示　移动  cmcc
</pre>

<pre>
table  is　{table}
current ip route show  :
default via {current_gateway} dev {current_dev} 

will exec the command:
{del_cmd}
{add_cmd}
</pre>

<h3>detect info:</h3>
<pre>
{detect_dict}
</pre>
"""
