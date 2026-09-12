#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
加密实现自检。

用固定的黄金向量核对 BitSrunLogin/encryption/ 下的四个加密函数，不需要联网，
也不需要 config.toml，因此可以用来判断「登录失败」到底是配置问题还是加密
实现被改坏了。

    python selftest.py

全部通过时退出码为 0，任一不符为 1。

这四个向量同时用于核对 `powershell` 分支的 `-SelfTest`：两个分支的加密实现
必须给出完全相同的结果，出现差异即说明其中一方移植有误。
"""
import sys

from BitSrunLogin.encryption.srun_base64 import get_base64
from BitSrunLogin.encryption.srun_md5 import get_md5
from BitSrunLogin.encryption.srun_sha1 import get_sha1
from BitSrunLogin.encryption.srun_xencode import get_xencode

# 与 powershell 分支 -SelfTest 共用的固定输入
KEY = "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789"
MSG = '{"username":"1234567890@dx","password":"pw","ip":"10.0.0.1","acid":"3","enc_ver":"srun_bx1"}'

# 黄金向量：由参考实现确定性地产生，逐字节固定
EXPECT = {
    'base64("132456")':
        '9F9x0JHI',
    'get_sha1("hello")':
        'aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d',
    'get_md5("pw", KEY)':
        '5bc328079a5dc482a40824390b37063f',
    'base64(get_xencode(MSG, KEY))':
        'ifmkGB9Vnhs0FHCIQZnATcecSSGyJulOcgodsvw3yrlMkXHH8K89aWgIPjkKlk8FH5'
        'TISo3NLpkQa7SaK0dkiodLIWXbUB8bMTf99+lOCH0jD5XuXVWTuvuQEyaBOxY0',
}


def check(name, actual):
    expected = EXPECT[name]
    if actual == expected:
        print(f'  OK   {name}')
        return True
    print(f'  FAIL {name}')
    print(f'       期望: {expected}')
    print(f'       实际: {actual}')
    return False


if __name__ == '__main__':
    # 注意 base64 一项：结果必须是 9F9x0JHI，若为 MTMyNDU2 说明误用了标准
    # base64 —— 深澜用的是自定义字母表，两者的输出完全不同。
    print(f'自定义 base64 字母表: {get_base64.__module__}')

    results = [
        check('base64("132456")', get_base64('132456')),
        check('get_sha1("hello")', get_sha1('hello')),
        check('get_md5("pw", KEY)', get_md5('pw', KEY)),
        check('base64(get_xencode(MSG, KEY))', get_base64(get_xencode(MSG, KEY))),
    ]

    if all(results):
        print('\n全部通过：加密实现与参考实现的输出逐字节一致。')
        sys.exit(0)
    print('\n存在不一致，加密实现可能已被改动。')
    sys.exit(1)
