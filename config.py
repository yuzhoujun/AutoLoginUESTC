#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
加载个人配置 config.toml。

学号 / 密码写在 config.toml 里(该文件已被 .gitignore 忽略)，
本文件只是加载器，不用改。
首次使用请把 config.example.toml 复制成 config.toml 再填。
"""
import tomllib
from collections import namedtuple
from pathlib import Path

User = namedtuple('User', ['user_id', 'passwd'])

CONFIG_FILE = Path(__file__).parent / 'config.toml'


def load_config(path=CONFIG_FILE):
    """读取 config.toml，返回可直接传给 LoginManager / always_login 的参数字典。"""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"找不到配置文件 {path}\n"
            f"请先把 config.example.toml 复制成 config.toml，并填上你的学号和密码。"
        )

    with open(path, 'rb') as f:
        cfg = tomllib.load(f)

    account = cfg['account']
    portal = cfg['portal']
    monitor = cfg.get('monitor', {})

    return {
        'user': User(str(account['username']), str(account['password'])),
        'url': portal['url'],
        'ac_id': str(portal['ac_id']),  # 校验和要按字符串拼接，而 toml 里写的是数字
        'domain': account.get('domain', '@dx'),

        # 下面的一般不用改。
        # test_ip 必须真的响应 ICMP：114.114.114.114 在电子科大宿舍网 100% 丢包，
        # 用它会让程序一直误判断网。223.5.5.5(阿里 DNS) 实测可达。
        'test_ip': monitor.get('test_ip', '223.5.5.5'),
        'delay': monitor.get('delay', 16),
        'max_failed': monitor.get('max_failed', 3),
    }


login_options = load_config()
