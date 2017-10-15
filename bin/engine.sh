#############
# 启动deroute服务
#############

#!/bin/sh
cmd='/usr/bin/python'
project_path=/devops/app/deroute
export PYTHONPATH=$project_path
pname=deroute



query()
{
	ps aux|grep -v grep|grep -q $pname&& echo "running" || echo "not running"
}

test()
{
    $cmd $project_path/engine.py 
    echo "start ..."
}

start()
{
    nohup $cmd $project_path/engine.py  &
}

stop()
{
    ps -ef| grep $pname |grep -v grep |awk '{print $2}'|xargs kill -9 > /dev/null 2>&1 &
}

restart () {
    stop
    start
}

case "$1" in
  test)
    test
    ;;
  start)
    start
	sleep 0.5
	query
    ;;
  stop)
    stop
	query
    ;;
  restart|reload|force-reload)
    restart
    ;;
  *)
    echo "Usage: $0 {test|start|stop|restart}"
esac
