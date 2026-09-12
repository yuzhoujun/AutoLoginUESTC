#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
日志配置。

同时输出到控制台和文件：控制台只显示 INFO 及以上，文件记录 DEBUG 及以上。
日志文件按日期命名，写在脚本同级的 logs/ 目录下，形如 logs/2026-09-13.log。

本文件为接入本仓库而新增。文件中被注释掉的 ConfigParser 段与 __main__ 段的
代码是参考实现遗留的配置读取逻辑，本项目改用 config.toml 后不再需要，保留以
便于对照。
"""

import time
import logging
from pathlib import Path

# from configparser import ConfigParser



# cfg = ConfigParser()
# cfg.read('./default.ini', encoding='utf-8')
# cfg.read('./custom.ini', encoding='utf-8')

def create_logger(loggername: str = 'logger', levelname: str = 'DEBUG', console_levelname='INFO'):
    levels = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }

    logger = logging.getLogger(loggername)
    logger.setLevel(levels[levelname])

    logger_format = logging.Formatter(
        "[%(asctime)s][%(levelname)s][%(filename)s][%(funcName)s][%(lineno)03s]: %(message)s")
    console_format = logging.Formatter("[%(levelname)s] %(message)s")

    handler_console = logging.StreamHandler()
    handler_console.setFormatter(console_format)
    handler_console.setLevel(levels[console_levelname])

    path = Path(__file__).parent/'logs'  # 日志目录
    # path = Path(cfg.get('prefers', 'logging_path'))
    path.mkdir(parents=True, exist_ok=True)
    today = time.strftime("%Y-%m-%d")  # 日志文件名
    common_filename = path / f'{today}.log'
    handler_common = logging.FileHandler(common_filename, mode='a+', encoding='utf-8')
    handler_common.setLevel(levels[levelname])
    handler_common.setFormatter(logger_format)

    logger.addHandler(handler_console)
    logger.addHandler(handler_common)

    return logger


# configs = dict(cfg._sections)
# caps = dict(configs['capability'])
# for key, value in caps.items():
#     if "true" == value.lower():
#         caps[key] = True
#     elif 'false' == value.lower():
#         caps[key] = False
#     else:
#         pass

# prefers = dict(configs['prefers'])
# for key, value in prefers.items():
#     if "true" == value.lower():
#         prefers[key] = True
#     elif 'false' == value.lower():
#         prefers[key] = False
#     else:
#         pass

# rules = dict(configs['rules'])
# 日志器名称沿用参考实现的 'wechat'（上游版本带微信推送），仅作标识用，无实际含义
logger = create_logger('wechat')

if __name__ == "__main__":
    # for k, v in caps.items():
    #     print(k, v)
    pass