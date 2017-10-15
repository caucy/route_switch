deroute switch 

一个控制路由表的探测，切换系统。

需求：

    三线服务器，当某条线路不可用的时候，这个线路出口的流量全部从其他可用出口出去。
实现方式：

    1，绑定 ip 去 ping 公网 ip ，类似 114.114.114.114 ，当某ip 丢包率达到阀值的时候去更改路由表出口网关。

    2，核心命令：
    ​    ​ping -i 0.2 -w 2 -c 10 -I bind_ip detect_ip 指定绑定 ip 去 ping。 
    ​    ​ip route add default via gate_ip dev gate_dev table n 新增 table n ,流量从gate_ip gate_dev 出去。
    ​    ​ip route del default via gate_ip dev gate_dev table n 删除 table n 的默认网关规则。
    ​    ​ip rule add from gate_ip dev to dst_ip table n pref m 新增路由规则，从gate_ip 出口流量到dst_ip 查路由表m
    ​3,  上面命令不依赖三方库，都是用subprocess 调用，目前没有 好的ping 的三方库。
    ​4，当执行切换操作，会mail 发送指定收件人。
    ​5，三线网关需要单独指定高优先级路由规则，否则会受 受探测的 table 影响。

启动：

    安装三方依赖 :
pip install -r requirement.txt

    启动：
sh bin/engine.sh

出现的问题：
    1，手动干扰路由表，会导致del add 异常。
    2，bind ip 优先级高于路由表指定rule ，更改table 出口网关，要使网卡ip不受table 规则影响，否则，出现用电信 ip  ping 出口网关指向移动 interface 将永远ping 不通。
    3，如果只有三线地址，监控的table如果涵盖了三个接口到跳板机的规则，将有可能出现，三线路由都更改，导致跳板机登陆不上去的情况。
    
