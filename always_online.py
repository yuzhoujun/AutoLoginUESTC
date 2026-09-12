#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
常驻运行：定时探测连通性，判定断网后自动重新登录。

用法：
    python always_online.py

程序在前台一直运行，按 Ctrl+C 退出。日志同时输出到控制台并写入
logs/<日期>.log。

注意：本脚本是**前台进程**，关闭终端窗口或注销会一并结束它，因此只适合用来
测试。需要开机自启、长期无人值守，请用 manage.py 注册计划任务或 Windows 服务：

    python manage.py install          注册计划任务（推荐，零依赖）
    python manage.py install-service  注册 Windows 服务（需 nssm 或 WinSW）
"""
import ctypes
import platform
import subprocess
import time
import traceback

from logger import logger
from BitSrunLogin.LoginManager import LoginManager
from config import login_options

HOST_NAME = platform.node()


def _now():
    return time.strftime('%Y-%m-%d %H:%M:%S')


def _disable_quick_edit():
    """
    关闭控制台的「快速编辑」模式。

    否则在窗口里点一下鼠标就会进入文本选择状态，进程的输出被挂起，看起来像
    卡死了。作为计划任务 / 服务运行时没有控制台，这里会失败，直接忽略即可。
    """
    try:
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-10), 128)
    except Exception:
        pass


def is_connect_internet(test_ip):
    """
    ping 一次 test_ip，通则认为在线。

    test_ip 必须是**确实响应 ICMP 的地址**。很多公共 DNS 屏蔽 ping，
    选了这类地址会导致程序一直误判为断网（详见 README 的说明）。
    """
    if platform.system().lower().startswith('windows'):
        cmd = ['ping', test_ip, '-n', '1', '-w', '1000']
    else:
        cmd = ['ping', test_ip, '-c', '1', '-W', '1']
    # 丢弃 ping 自身的输出，只看退出码；否则每轮都会往日志里刷一大段文本
    return subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0


def always_login(user=None, test_ip=None, delay=16, max_failed=3, **kwargs):
    """
    监控循环：探测 -> 判定 -> 重新登录。

    探测失败时逐渐缩短间隔，以便网络恢复后能尽快重连，但**有下限**，且一旦
    发起过登录尝试就立即复位。原实现为 `delay = max(0., delay / 2)`，既没有
    下限也不复位：只要探测点持续不可达，delay 就会衰减到 0，循环失去等待，
    退化成每秒一次的登录请求，长时间运行会持续冲击认证服务器。

    其余参数（url / ac_id / domain 等）通过 **kwargs 透传给 LoginManager。
    """
    org_delay = delay
    min_delay = max(2, org_delay // 8)
    failed = 0
    was_offline = False

    logger.info(f'[{_now()}] [{HOST_NAME}] 网络监控启动 '
                f'(test_ip={test_ip}, delay={delay}s, max_failed={max_failed})')

    while True:
        if not is_connect_internet(test_ip):
            failed += 1
            if failed >= max_failed:
                logger.info(f'[{_now()}] [{HOST_NAME}] 检测到断网，尝试重新登录...')
                try:
                    result = LoginManager(**kwargs).login(
                        username=user.user_id, password=user.passwd)
                    logger.info(f'[{_now()}] [{HOST_NAME}] 登录结果: {result}')
                except Exception:
                    # 单次登录失败不影响后续轮次，记录下来继续探测
                    logger.error(f'[{_now()}] [{HOST_NAME}] 登录失败:\n{traceback.format_exc()}')

                # 已经尝试过一次登录：重新计数并把间隔复位。
                # 不复位的话，只要探测点本身一直不通，delay 就会停在最小值上
                # 无限重试。
                was_offline = True
                failed = 0
                delay = org_delay
            else:
                delay = max(min_delay, delay // 2)
        else:
            if was_offline:
                logger.info(f'[{_now()}] [{HOST_NAME}] 已恢复在线。')
                was_offline = False
            failed = 0
            delay = org_delay

        time.sleep(delay)


if __name__ == '__main__':
    _disable_quick_edit()
    # 兜底：无论出什么意外都记录下来、等一会儿重来，不让守护进程直接死掉
    while True:
        try:
            always_login(**login_options)
        except KeyboardInterrupt:
            logger.info('收到 Ctrl+C，退出。')
            break
        except Exception:
            logger.error(traceback.format_exc())
            time.sleep(15)
