#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
登录一次就退出，用于验证 config.toml 配置是否正确。

用法：先在浏览器里手动注销、断开网络，再执行 `python login_once.py`。
输出 "The loggin result is: ok" 表示配置正确。

需要常驻、掉线自动重连请改用 always_online.py。
"""
from BitSrunLogin.LoginManager import LoginManager
from config import login_options

if __name__ == '__main__':
    user = login_options['user']
    # login_options 里的 url / ac_id / domain / test_ip 等参数由 LoginManager 的
    # __init__ 接收，这里只需额外传入账号密码
    LoginManager(**login_options).login(username=user.user_id, password=user.passwd)
