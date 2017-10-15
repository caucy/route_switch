# -*- coding:utf-8 -*-
import subprocess


def external_cmd(cmd, msg_in=''):
    try:
        proc = subprocess.Popen(cmd,
                                shell=True,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        stdout_value, stderr_value = proc.communicate(msg_in)
        return proc, stdout_value.rstrip("\n"), stderr_value.rstrip("\n")
    except ValueError:
        return proc, None, None


