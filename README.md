# UESTC 电子科技大学校园网认证 —— Python 实现

本分支使用 Python 实现电子科技大学校园网（深澜 srun 认证）的自动登录与掉线自动
重连，并提供注册为开机自启后台进程的管理脚本。

配置通过独立的 `config.toml` 提供，个人凭据不进入仓库，无需修改代码。

> 本分支为 Python 实现，PowerShell 版见 [`powershell` 分支](../../tree/powershell)，
> 项目总说明与两个版本的对比见 [`main` 分支](../../tree/main)。
> 两个版本功能等价，可任选其一。

---

## 一、与参考仓库的关系

本分支的认证实现以及常驻脚本，来源于
[coffeehat/BIT-srun-login-script](https://github.com/coffeehat/BIT-srun-login-script)，
并在此基础上做了修改与扩展。因此本分支保留了上游作者的版权声明，详见「九、声明」。

### 1.1 派生自参考仓库的文件

| 文件 | 说明 |
| --- | --- |
| `BitSrunLogin/`（整个目录） | 深澜认证流程与加密实现，复制自参考仓库 |
| `always_online.py` | 参考仓库中存在同名脚本，本项目的版本在其基础上重写，详见 1.2 |

### 1.2 对参考实现的修改

| 文件 | 修改内容 |
| --- | --- |
| `BitSrunLogin/LoginManager.py` | 修复本机 IP 解析逻辑（见下）；补充类与方法说明；`login()` 现在返回认证结果；移除未被调用的 base64 编解码方法与 `decode` 参数；删除因拼写错误（`__mian__`）而永不执行的 `__main__` 块 |
| `BitSrunLogin/encryption/srun_xencode.py` | 加密逻辑未改动；移除未被调用的 `force()`；`__main__` 由 `print(type(...))` 改为可执行的断言自检 |
| `BitSrunLogin/encryption/srun_base64.py` | 加密逻辑未改动，仅补充注释 |
| `BitSrunLogin/encryption/srun_md5.py`、`srun_sha1.py` | 加密逻辑未改动，仅补充注释 |
| `always_online.py` | 接入 `config.toml`（上游为脚本内硬编码账号）；改用 `logger` 记录日志（上游为 `print`）；增加连续失败判定 `max_failed` 与探测间隔衰减；`ping` 参数按操作系统选择（上游固定用 `-c`，是 Linux 语法，在 Windows 上无效）；循环内单次登录失败不再中断整个进程 |

**IP 解析的修复**：新版认证页将本机 IP 置于 JavaScript 的 `var CONFIG = {...}` 中
（旧版页面才是隐藏的 `id="user_ip"` 输入框），并且登录页在部分场景下只是一个
`<meta http-equiv="refresh">` 跳转壳。原实现在此情形下会因正则匹配不到而抛出
`AttributeError: 'NoneType' object has no attribute 'group'`，导致登录失败。

修复方式为两步：

1. `_get_login_page` 先识别并跟随 meta refresh 跳转，取到真实的认证页
   （`requests` 不会自动跟随该跳转）。
2. `_resolve_ip_from_login_page` 同时兼容新旧两种页面格式，依次尝试匹配
   `var CONFIG` 中的 `ip` 字段与旧版的 `id="user_ip"` 输入框。

### 1.3 本项目新增的部分

以下文件参考仓库中不存在，为接入本仓库而新增：

```text
config.py               读取 config.toml 的加载器
config.example.toml     配置模板
login_once.py           登录一次，用于验证配置
logger.py               日志
selftest.py             加密实现自检（四项黄金向量）
manage.py               自启注册与运行管理（计划任务 / Windows 服务）
autoConnectNetwork.bat  Windows 双击启动器
```

### 1.4 与 PowerShell 分支的关系

`powershell` 分支与本分支相互独立：该分支的依据是深澜认证协议本身，未使用参考仓库
的代码。两者仅共用同一套协议，实现互不衍生。

---

## 二、环境要求

| 项目 | 要求 |
| --- | --- |
| 操作系统 | Windows / Linux / macOS |
| Python | 3.11 或更高版本（配置读取使用标准库 `tomllib`） |
| 第三方依赖 | `requests` |

```bash
pip install requests
```

**开机自启仅限 Windows**（依赖任务计划程序或 Windows 服务）。本分支的认证与常驻
功能本身跨平台，但 `manage.py` 的自启子命令只在 Windows 上可用。

> 本分支的操作系统兼容性来自 Python 与 `requests`，未在 macOS 上实测。
> 本项目实测环境见「四、验证」。

---

## 三、使用方法

### 3.1 获取代码

```bash
git clone -b python https://github.com/yuzhoujun/AutoLoginUESTC.git
cd AutoLoginUESTC
```

### 3.2 创建个人配置

仓库中只提供模板 `config.example.toml`。将其复制为 `config.toml`：

```bash
# Windows
copy config.example.toml config.toml

# Linux / macOS
cp config.example.toml config.toml
```

`config.toml` 已在 `.gitignore` 中忽略，不会被提交到仓库，可填写真实密码。

```toml
[account]
username = "202912272625"   # 学号
password = "your_password"  # 教务处密码
domain   = "@dx"            # 电信 @dx / 移动 @cmcc / 校园网 @dx-uestc

[portal]
url    = "http://10.253.0.235"  # 寝室公寓；主楼有线为 http://10.253.0.237
ac_id  = 3                      # 寝室公寓 3；主楼有线 1

[monitor]
test_ip    = "223.5.5.5"        # 用于判断连通性的地址，须响应 ICMP
delay      = 16                 # 掉线检测间隔（秒）
max_failed = 3                  # 连续失败几次判定为断网
```

### 3.3 自检与验证配置

先确认加密实现未被破坏（不需要联网，也不需要 `config.toml`）：

```bash
python selftest.py
```

输出 `全部通过：加密实现与参考实现的输出逐字节一致。` 表示实现正确。

再在浏览器中手动注销、断开网络，然后执行：

```bash
python login_once.py
```

输出 `The loggin result is: ok` 表示配置正确；结果不是 `ok` 时以非 0 退出码结束。

> 该命令会打印认证服务器返回的完整 JSON，其中包含 `access_token`。该字段是本次
> 会话的临时凭证，请勿将这段输出粘贴到公开场合。

### 3.4 前台运行

```bash
python always_online.py
```

程序按 `delay` 间隔 ping `test_ip`，连续失败 `max_failed` 次即判定断网并重新登录。
日志同时输出到控制台并写入 `logs/<日期>.log`（例如 `logs/2026-09-13.log`）。

**这是前台进程，关闭终端窗口或注销会一并结束它，因此只适合测试。** 需要开机自启、
长期无人值守，请使用 3.6 的自启注册。

### 3.5 双击运行

`autoConnectNetwork.bat` 是双击启动器，双击后进入交互菜单：

```text
  UESTC 校园网自动登录
   1. 登录一次（验证配置是否正确）
   2. 前台常驻运行（仅用于测试，关掉终端就停）
   3. 注册开机自启 —— 计划任务（推荐，零依赖）
   4. 注销计划任务
   5. 启动计划任务
   6. 停止计划任务
   7. 注册 Windows 服务（需 nssm/WinSW）
   8. 注销 Windows 服务
   9. 查看当前状态
  10. 加密实现自检
   0. 退出
```

也可以带参数直接执行某一步，跳过菜单：

```bat
autoConnectNetwork.bat once        :: 登录一次
autoConnectNetwork.bat install     :: 注册开机自启
autoConnectNetwork.bat status      :: 查看状态
```

涉及注册 / 注销的命令会自动请求管理员权限（弹出 UAC），其余命令不需要。

`autoConnectNetwork.bat` 本身是**纯 ASCII** 文件，中文全部由 Python 脚本输出。
原因见「七、常见问题」中关于编码的说明。

#### 解释器的查找顺序

双击启动时 bat 按以下顺序寻找 Python，取第一个能 `import requests` 的：

1. 环境变量 `PYTHON`
2. 本项目目录下的 `python-path.txt`（由 `manage.py install` 自动写入）
3. 环境变量 `CONDA_PREFIX` 指向的解释器
4. PATH 上的 `python`、`py`
5. anaconda / miniconda 的常见安装位置

其中第 4 步会**实际执行**候选程序来验证，而不是只看文件名。原因是 PATH 上的
`python.exe` 常常是微软商店的占位程序（位于
`%LOCALAPPDATA%\Microsoft\WindowsApps`），它不执行任何代码、直接返回 9009。

> **conda 用户注意**：conda 只将 `安装目录\Scripts` 加入 PATH，而 `python.exe`
> 位于安装目录**根目录**下。因此双击 bat 时 `python` 可能解析到上述占位程序。
> 此时可以显式指定，或用一次第 3 步的环境变量：
>
> ```bat
> set PYTHON=D:\APP-D\anaconda3\python.exe
> autoConnectNetwork.bat
> ```
>
> 执行过一次 `python manage.py install` 后，解释器路径会记入 `python-path.txt`，
> 之后双击即可直接工作。

### 3.6 开机自启

提供两种互斥的方式，任选其一。**推荐计划任务**：零依赖，且功能上已经足够。

#### 方式一：计划任务（推荐）

```bash
python manage.py install      # 注册
python manage.py start        # 立即启动
python manage.py status       # 查看状态
python manage.py stop         # 停止
python manage.py uninstall    # 注销
```

注册后的任务具有以下配置：

| 项目 | 取值 | 原因 |
| --- | --- | --- |
| 运行身份 | `SYSTEM` | 认证按机器 IP 进行，与桌面会话无关；注销后仍可运行，且无需存储账号密码 |
| 触发器 | 开机后 30 秒 | 避开系统刚启动时网络栈尚未就绪的阶段 |
| 运行时长限制 | 不限制 | 默认上限为 72 小时，到点会强制结束任务，对常驻守护进程是致命的 |
| 失败重启 | 1 分钟后重试，最多 999 次 | 进程异常退出后自动拉起 |
| 多实例策略 | 不启动新实例 | 避免两个进程同时反复登录 |
| 电源策略 | 使用电池时照常运行 | 笔记本切换到电池时不被中止 |

这些设置无法通过 `schtasks` 的命令行参数表达（尤其是「不限制运行时长」和「失败
重启」），因此 `manage.py` 生成任务 XML 后用 `schtasks /Create /XML` 导入。

注册前会检查 `config.toml` 是否存在，避免任务在每次开机后立刻失败。

#### 方式二：Windows 服务

```bash
python manage.py install-service     # 注册
python manage.py uninstall-service   # 注销
```

**Python 脚本不能直接注册为 Windows 服务**：服务必须实现 SCM 的 `ServiceMain`
回调并按协议上报状态，解释型脚本做不到。因此需要一个包装器把普通进程托管成服务，
本项目支持 [nssm](https://nssm.cc/download) 与
[WinSW](https://github.com/winsw/winsw/releases)。

本机没有包装器时，脚本会打印下载地址后退出，**不会自动下载第三方二进制**。
这一点与 `powershell` 分支的处理一致。

### 3.7 管理命令一览

```text
python manage.py                 交互式菜单
python manage.py once            登录一次（等价于 login_once.py）
python manage.py run             前台常驻（等价于 always_online.py）
python manage.py selftest        加密实现自检（等价于 selftest.py）
python manage.py install         注册计划任务          ← 需要管理员
python manage.py uninstall       注销计划任务          ← 需要管理员
python manage.py start           启动计划任务          ← 需要管理员
python manage.py stop            停止计划任务          ← 需要管理员
python manage.py install-service 注册 Windows 服务     ← 需要管理员
python manage.py uninstall-service 注销 Windows 服务   ← 需要管理员
python manage.py status          查看当前状态
```

---

## 四、验证

### 4.1 实测结果

以下结果于 **2026-09-13** 在电子科技大学宿舍网环境实测：

| 项目 | 结果 |
| --- | --- |
| `python selftest.py` | 四项黄金向量逐字节一致，退出码 0 |
| `python login_once.py` | 返回 `"error":"ok"` |
| 加密函数输出 | 与参考实现逐字节一致 |
| 监控循环节流 | 判定断网后按 `delay` 间隔重试，未出现无间隔重试 |
| `manage.py install` | 计划任务创建成功，XML 中 `ExecutionTimeLimit=PT0S`、重启策略、`SYSTEM` 身份均已生效 |
| `manage.py start` | 守护进程以 SYSTEM 身份运行，正常写入 `logs/` |
| `manage.py uninstall` | 计划任务与守护进程均被清除，无残留进程 |
| `autoConnectNetwork.bat` | 双击可用；能跳过微软商店占位程序找到可用解释器 |

支持的接入方式（2026-09-13 验证）：

```text
- 校园网有线接入 + 学号认证（主楼）
- 移动 / 电信寝室宽带有线接入 + 学号认证（硕丰 6、7、8 组团等插网线弹出认证页面的场景）
```

### 4.2 加密函数自检

`python selftest.py` 用四项固定的黄金向量核对 `BitSrunLogin/encryption/` 下的四个
加密函数，不需要联网，也不需要 `config.toml`，因此可用于区分「登录失败」是配置
问题还是加密实现被改坏：

```text
base64("132456")                    ->  9F9x0JHI
get_sha1("hello")                   ->  aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d
get_md5("pw", KEY)                  ->  5bc328079a5dc482a40824390b37063f
base64(get_xencode(MSG, KEY))       ->  ifmkGB9Vnhs0FHCIQZnATcecSSGyJulOcgodsvw3y...
```

其中 base64 一项用于确认自定义字母表正确 —— 若得到 `MTMyNDU2`（`"132456"` 的标准
base64），说明误用了标准库的 `base64` 实现。

这四项与 `powershell` 分支的 `-SelfTest` 使用同一组输入与期望值，两个分支的加密
实现必须给出完全相同的结果；出现差异即说明其中一方移植有误。

### 4.3 已修复的缺陷

以下两个缺陷曾存在于本分支，现已修复。二者来源不同，故分别说明。

#### （1）监控循环的重试间隔衰减没有下限

原实现为 `delay = max(0., delay / 2)`，衰减既无下限、登录尝试后也不复位。当探测点
持续不可达时 `delay` 会衰减到 0，循环失去等待，退化为每秒一次的登录请求。

该逻辑是**本项目在扩展上游 `always_online.py` 时引入的**：上游脚本只有固定间隔
`sleep(checkinterval)`，没有衰减。修复方式是设置下限
（`max(2, delay // 8)`），并在每次登录尝试后把间隔复位。实测：断网时重试间隔稳定
保持在 `delay` 上，对照修复前的序列 `16 → 8 → 4 → 2 → 1 → 0.5 → …`（40 秒内会
发出数百次登录请求）。

#### （2）默认探测点不可达

`config.example.toml` 与 `config.py` 中的默认探测点为 `114.114.114.114`。该地址在
电子科技大学宿舍网 **100% 丢包**，会导致程序持续判定断网并反复重登，即使网络实际
正常。

该默认值**继承自参考仓库**（上游 `always_online.py` 中为
`testip = "114.114.114.114"`）。现已改为 `223.5.5.5`（阿里 DNS），并于 2026-09-13
验证可达。选用其他地址前请自行确认：

```bat
ping -n 3 223.5.5.5
```

输出 `Lost = 0 (0% loss)` 方可使用。

---

## 五、配置项

| 字段 | 说明 |
| --- | --- |
| `account.username` | 学号 |
| `account.password` | 教务处密码 |
| `account.domain` | 网络提供商：电信 `@dx`、移动 `@cmcc`、校园网 `@dx-uestc` |
| `portal.url` | 认证页地址：寝室公寓 `http://10.253.0.235`，主楼有线校园网 `http://10.253.0.237` |
| `portal.ac_id` | 认证页 URL 中的 `ac_id` 参数：寝室公寓 `3`，主楼有线 `1` |
| `monitor.test_ip` | 用于判断连通性的地址，须响应 ICMP |
| `monitor.delay` | 掉线检测间隔（秒），默认 16 |
| `monitor.max_failed` | 连续探测失败多少次判定为断网，默认 3 |

`url` 与 `ac_id` 的确认方法：在浏览器中打开 `url`，认证页地址形如
`http://10.253.0.235/srun_portal_pc?ac_id=3&theme=pro`，其中的 `ac_id` 即为所需值。

> `config.py` 只是配置加载器，将 `config.toml` 读取为程序使用的字典，
> **不需要修改**。其中 `ac_id` 会被转为字符串，因为计算校验和时需要按字符串拼接，
> 而 TOML 中写的是数字。

---

## 六、代码说明

```text
AutoLoginUESTC/
├── config.example.toml      配置模板（提交至仓库）
├── config.toml              个人配置（已 gitignore，不提交）
├── python-path.txt          本机解释器路径（已 gitignore，由 manage.py 写入）
├── config.py                配置加载器
├── login_once.py            登录一次，用于验证配置
├── always_online.py         常驻运行，掉线自动重连
├── selftest.py              加密实现自检
├── manage.py                自启注册与运行管理
├── logger.py                日志，写入 logs/
├── autoConnectNetwork.bat   Windows 双击启动器（纯 ASCII）
├── logs/                    运行日志（已 gitignore）
└── BitSrunLogin/            深澜认证实现
    ├── LoginManager.py      登录流程
    ├── _decorators.py       参数检查与日志装饰器
    └── encryption/
        ├── srun_base64.py   自定义字母表的 base64
        ├── srun_md5.py      HMAC-MD5，密码摘要
        ├── srun_sha1.py     SHA1，校验和
        └── srun_xencode.py  XXTEA，加密 info
```

### 认证流程

`LoginManager.login()` 串起三步，实现的是同一套深澜认证协议：

```text
login(username, password)
 ├─ get_ip()               GET {portal}/              从页面中解析 ip
 │   ├─ _get_login_page()          取认证页，跟随 meta refresh 跳转
 │   └─ _resolve_ip_from_login_page()
 ├─ get_token()            GET /cgi-bin/get_challenge
 │   ├─ _get_challenge()
 │   └─ _resolve_token_from_challenge_response()
 └─ get_login_responce()   GET /cgi-bin/srun_portal?action=login&...
     ├─ _generate_encrypted_login_info()
     │   ├─ _generate_info()       拼接 info 字符串
     │   ├─ _encrypt_info()        XXTEA + 自定义 base64，加 "{SRBX1}" 前缀
     │   ├─ _generate_md5()        HMAC-MD5
     │   ├─ _encrypt_md5()         加 "{MD5}" 前缀
     │   ├─ _generate_chksum()     拼接校验串（顺序见下）
     │   └─ _encrypt_chksum()      SHA1，得到最终的 chksum
     ├─ _send_login_info()
     └─ _resolve_login_responce()
```

`login()` 返回认证服务器返回的 `error` 字段，`'ok'` 即成功。调用方据此判断本次
登录结果，例如 `always_online.py` 会把它写进日志。

校验串的拼接顺序固定为：`token+username`、`token+md5`、`token+ac_id`、`token+ip`、
`token+n`、`token+vtype`、`token+info`，其中 `n` 固定为 `200`、`vtype` 固定为 `1`。
顺序错则 chksum 不匹配，认证服务器会直接拒绝。

实现时需注意的三点，代码内均有对应注释：

1. **密码字段不是普通 MD5**，而是 `HMAC-MD5`，key 为 token、message 为密码明文。
2. **Base64 使用自定义字母表**，并非标准 Base64，不能用标准库的 `base64` 代替。
3. **本机 IP 的获取方式已变更**，且登录页可能是 meta refresh 跳转壳，详见「1.2」。

### 监控循环

`always_online.py` 的 `always_login()` 是常驻循环：探测 → 判定 → 重新登录。

```text
每轮：
  ping test_ip
   ├─ 不通：failed += 1
   │    ├─ failed >= max_failed → 尝试登录，之后 failed 归零、间隔复位
   │    └─ 否则                 → 间隔减半，但不低于 max(2, delay // 8)
   └─ 通：  failed 归零、间隔复位
  sleep(间隔)
```

单次登录失败会被捕获并记入日志，不影响后续轮次；进程级的异常由 `__main__` 的
外层循环兜底，记录后等待 15 秒重来，不让守护进程直接退出。

### 加密实现中的混淆常量

`srun_xencode.py` 中出现的多个位运算常量来自经过混淆的原始实现，容易误读。
实际上：

| 写法 | 实际值 |
| --- | --- |
| `0x86014019 \| 0x183639A0` | `0x9E3779B9`，XXTEA 标准 delta |
| `0x8CE0D9BF \| 0x731F2640` | `0xFFFFFFFF` |
| `0xEFB8D130 \| 0x10472ECF` | `0xFFFFFFFF` |
| `0xBB390742 \| 0x44C6F8BD` | `0xFFFFFFFF` |

即全部都是掩码，写成两个数按位或只是混淆手法。代码内已就地注释。

---

## 七、常见问题

**`FileNotFoundError: 找不到配置文件 .../config.toml`**
未复制模板。执行 `copy config.example.toml config.toml` 后填写账号信息。

**双击 bat 提示 `No usable Python found`**
bat 未能在候选项中找到可用的解释器，见「3.5 解释器的查找顺序」。最快的方式是显式
指定绝对路径：

```bat
set PYTHON=D:\APP-D\anaconda3\python.exe
autoConnectNetwork.bat
```

**双击 bat 提示 `python 不是内部或外部命令`**
Python 不在 PATH 中。注意 conda 只将 `安装目录\Scripts` 加入 PATH，而 `python.exe`
位于安装目录根目录下，因此 PATH 上的 `python` 可能是微软商店的占位程序（执行返回
9009）。处理方式同上。

**`ModuleNotFoundError: No module named 'requests'`**
解释器选对了但没有装依赖：

```bash
python -m pip install requests
```

**bat 文件为什么不能写中文？**
`.bat` 含非 ASCII 字符时两种编码都不可靠：存为 UTF-8，GBK 控制台会把中文片段当作
命令执行（它们不是合法的命令名）；存为 GBK，同样的文件在 UTF-8 控制台上显示为
乱码。控制台的代码页不在程序的控制范围内，因此唯一稳妥的做法是本文件保持纯 ASCII，
中文全部由 Python 输出 —— Python 3.6 起通过 Windows 控制台 Unicode API 写屏，在
各种代码页下都能正确显示。

**`Failed to resolve IP` / `Cannot find local ip in login page html`**
`url` 或 `ac_id` 配置有误，或认证页结构再次变更。请先在浏览器中打开认证页确认地址。

**登录成功但随即掉线**
`domain` 配置有误。电信为 `@dx`，移动为 `@cmcc`，校园网为 `@dx-uestc`。

**日志持续输出「检测到断网」**
`test_ip` 指向了不响应 ICMP 的地址。见「4.3 已修复的缺陷」第（2）条，并自行确认：

```bat
ping -n 3 223.5.5.5
```

**注册自启后日志没有更新**
先确认任务状态：`python manage.py status`。若显示已注册但守护进程未运行，检查
`config.toml` 是否存在且内容正确 —— 任务以 SYSTEM 身份运行，读取的是同一个
`config.toml`，但工作目录为项目目录，不要移动该文件。

**休眠期间不登录**
计划任务在休眠 / 睡眠时不执行。如需在唤醒后尽快恢复，任务已设置
`StartWhenAvailable`，错过的启动会在系统可用时补执行；也可在「任务计划程序」中勾选
「唤醒计算机运行此任务」，或将机器设为不睡眠。

---

## 八、运行日志

日志由 `logger.py` 写入 `logs/` 目录，按日期命名，已随 `.gitignore` 忽略。日志内容
与 `powershell` 分支一致，均为每次登录尝试的结果。

日志同时输出到控制台（INFO 及以上）和文件（DEBUG 及以上）。注册为计划任务后没有
控制台，此时只有文件日志可用。

---

## 九、声明

### 许可

本项目采用 [MIT 许可证](LICENSE)。

本分支的认证实现（`BitSrunLogin/`）与常驻脚本（`always_online.py`）来源于
[coffeehat/BIT-srun-login-script](https://github.com/coffeehat/BIT-srun-login-script)，
因此 `LICENSE` 中保留了上游作者的版权声明（`Copyright (c) 2020 coffeehat`）。
这是 MIT 许可证的要求，请勿删除。其后一行是本项目对自身修改部分的声明。

### 参考

- [coffeehat/BIT-srun-login-script](https://github.com/coffeehat/BIT-srun-login-script)
  —— 本分支认证实现的来源，深澜认证流程的公开实现。该仓库另提供支持 OpenWrt 的
  Go 版本。
- 深澜认证被多所高校采用，GitHub 上存在较多同类实现，遇到问题时可供对照参考。

### 免责声明

本项目仅供个人学习与自用。请仅在自己的账号上使用，不得用于批量登录他人账号或任何
未经授权的用途。账号密码仅保存在本地被 gitignore 忽略的 `config.toml` 中，不会上传
至任何服务器；但若因手动提交导致泄露，责任由使用者自负，提交前请确认
`git status` 的输出。
