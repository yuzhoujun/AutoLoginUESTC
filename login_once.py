#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
登录一次就退出，用于验证 config.toml 配置是否正确。

用法：先在浏览器里手动注销、断开网络，再执行 `python login_once.py`。
输出 "The loggin result is: ok" 表示配置正确；结果不是 ok 时以非 0 退出码结束，
便于脚本判断。

需要常驻、掉线自动重连请改用 always_online.py，或直接用 manage.py 注册自启。
"""
import sys

from BitSrunLogin.LoginManager import LoginManager
from config import login_options

if __name__ == '__main__':
    user = login_options['user']
    # 只透传认证相关参数：test_ip / delay / max_failed 是监控用的，LoginManager
    # 不需要（它的 kwargs 会全部并进 self.args）。
    result = LoginManager(
        url=login_options['url'],
        ac_id=login_options['ac_id'],
        domain=login_options['domain'],
    ).login(username=user.user_id, password=user.passwd)

    if result != 'ok':
        sys.exit(1)
