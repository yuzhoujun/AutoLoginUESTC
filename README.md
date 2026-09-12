# UESTC 电子科技大学校园网认证 —— Python 实现

本分支使用 Python 实现电子科技大学校园网（深澜 srun 认证）的自动登录与掉线自动
重连。认证实现复制自参考仓库并在此基础上做了修改，详见下文。

配置通过独立的 `config.toml` 提供，个人凭据不进入仓库，无需修改代码。

> 本分支为 Python 实现，PowerShell 版见 [`powershell` 分支](../../tree/powershell)，
> 项目总说明与两个版本的对比见 [`main` 分支](../../tree/main)。
> 两个版本功能等价，可任选其一。

---

## 一、与参考仓库的关系

**本分支的认证实现（`BitSrunLogin/` 目录）复制自**
**[coffeehat/BIT-srun-login-script](https://github.com/coffeehat/BIT-srun-login-script)**，
并在此基础上做了修改与优化。因此本分支保留了上游作者的版权声明，详见「九、声明」。

### 对参考实现的修改

| 文件 | 修改内容 |
| --- | --- |
| `BitSrunLogin/LoginManager.py` | 修复本机 IP 解析逻辑（见下）；补充类与方法说明 |
| `BitSrunLogin/encryption/*.py` | 加密逻辑未改动，仅补充注释 |
| 其余文件 | 本项目新增，非参考仓库内容 |

**IP 解析的修复**：新版认证页将本机 IP 置于 JavaScript 的 `var CONFIG = {...}` 中
（旧版页面才是隐藏的 `id="user_ip"` 输入框），并且登录页在部分场景下只是一个
`<meta http-equiv="refresh">` 跳转壳。原实现在此情形下会因正则匹配不到而抛出
`AttributeError: 'NoneType' object has no attribute 'group'`，导致登录失败。

修复方式为两步：

1. `_get_login_page` 先识别并跟随 meta refresh 跳转，取到真实的认证页
   （`requests` 不会自动跟随该跳转）。
2. `_resolve_ip_from_login_page` 同时兼容新旧两种页面格式，依次尝试匹配
   `var CONFIG` 中的 `ip` 字段与旧版的 `id="user_ip"` 输入框。

### 本项目新增的部分

以下文件为接入本仓库而新增，不属于参考仓库：

```text
config.py               读取 config.toml 的加载器
config.example.toml     配置模板
login_once.py           登录一次，用于验证配置
always_online.py        常驻运行，掉线自动重连
logger.py               日志
autoConnectNetwork.bat  Windows 双击启动器
```

### 与 PowerShell 分支的关系

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

### 3.3 验证配置

在浏览器中手动注销、断开网络，然后执行：

```bash
python login_once.py
```

输出 `The loggin result is: ok` 表示配置正确。

> 该命令会打印认证服务器返回的完整 JSON，其中包含 `access_token`。该字段是本次
> 会话的临时凭证，请勿将这段输出粘贴到公开场合。

### 3.4 常驻运行

```bash
python always_online.py
```

程序按 `delay` 间隔 ping `test_ip`，连续失败 `max_failed` 次即判定断网并重新登录。
日志同时输出到控制台并写入 `logs/<日期>.log`（例如 `logs/2026-09-13.log`）。

### 3.5 双击运行 / 开机自启

`autoConnectNetwork.bat` 是双击启动器，默认执行 `login_once.py`。如需常驻重连，
将其中的 `login_once.py` 改为 `always_online.py`。

若双击后提示 `python 不是内部或外部命令`，说明 Python 不在 PATH 中，需在 bat 中
显式指定解释器的绝对路径：

```bat
set "PYTHON=D:\APP-D\anaconda3\python.exe"
```

> **conda 用户注意**：conda 只将 `安装目录\Scripts` 加入 PATH，而 `python.exe`
> 位于安装目录**根目录**下。因此双击 bat 时 `python` 可能解析到
> `C:\Users\<用户名>\AppData\Local\Microsoft\WindowsApps\python.exe` —— 这是
> 微软商店的占位程序，执行会直接返回 9009。此时必须使用绝对路径。

开机自启：将 bat 的快捷方式放入启动文件夹（Win+R 输入 `shell:startup`）。
如需更强的自启与保活能力，可参考
[`powershell` 分支的注册脚本](../../tree/powershell#readme)（其计划任务方案与
本分支的脚本亦可组合使用，因其本质是调用命令行）。

---

## 四、验证

### 4.1 实测结果

以下结果于 **2026-09-13** 在电子科技大学宿舍网环境实测：

| 项目 | 结果 |
| --- | --- |
| `python login_once.py` | 返回 `"error":"ok"` |
| 加密函数输出 | 与参考实现逐字节一致 |
| `autoConnectNetwork.bat` | 可正常启动 |

支持的接入方式（2026-09-13 验证）：

```text
- 校园网有线接入 + 学号认证（主楼）
- 移动 / 电信寝室宽带有线接入 + 学号认证（硕丰 6、7、8 组团等插网线弹出认证页面的场景）
```

### 4.2 加密函数自检

本分支未内置自检命令，可用以下方式核对加密实现。期望输出为：

```text
base64("132456")  ->  9F9x0JHI          （标准 base64 则为 MTMyNDU2）
get_sha1("hello") ->  aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d
```

其中 base64 一项用于确认自定义字母表正确 —— 若得到 `MTMyNDU2`，说明误用了标准
base64 实现。

`powershell` 分支内置了更完整的 `-SelfTest`（覆盖 XXTEA 与 HMAC-MD5），如需交叉
验证可参考该分支。

### 4.3 已知问题

以下两个问题存在于本分支，**已在 [`powershell` 分支修复](../../tree/powershell)**，
本分支保留原状。

#### （1）监控循环的重试间隔无下限

`always_online.py` 中为 `delay = max(0., delay / 2)`，衰减没有下限，且登录尝试后
不复位。当探测点持续不可达时 `delay` 会衰减到 0，循环失去等待，形成每秒一次的
登录请求，长时间运行会持续冲击认证服务器。

建议：将衰减设为有下限，并在每次登录尝试后复位间隔。

#### （2）默认探测点不可达

`config.example.toml` 与 `config.py` 中的默认探测点为 `114.114.114.114`。该地址在
电子科技大学宿舍网 **100% 丢包**，会导致程序持续判定断网并反复重登，即使网络实际
正常。

建议：改为 `223.5.5.5`（阿里 DNS）或 `119.29.29.29`（腾讯 DNS），两者均于
2026-09-13 验证可达。选用前请自行确认：

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
├── config.py                配置加载器
├── login_once.py            登录一次，用于验证配置
├── always_online.py         常驻运行，掉线自动重连
├── logger.py                日志，写入 logs/
├── autoConnectNetwork.bat   Windows 双击启动器
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

校验串的拼接顺序固定为：`token+username`、`token+md5`、`token+ac_id`、`token+ip`、
`token+n`、`token+vtype`、`token+info`，其中 `n` 固定为 `200`、`vtype` 固定为 `1`。
顺序错则 chksum 不匹配，认证服务器会直接拒绝。

实现时需注意的三点，代码内均有对应注释：

1. **密码字段不是普通 MD5**，而是 `HMAC-MD5`，key 为 token、message 为密码明文。
2. **Base64 使用自定义字母表**，并非标准 Base64，不能用标准库的 `base64` 代替。
3. **本机 IP 的获取方式已变更**，且登录页可能是 meta refresh 跳转壳，详见「一、与
   参考仓库的关系」。

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

**`python 不是内部或外部命令`，或双击 bat 一闪而过**
Python 不在 PATH 中，见「3.5 双击运行 / 开机自启」。bat 末尾有 `pause`，报错信息
会停留在窗口中。

**`Failed to resolve IP` / `Cannot find local ip in login page html`**
`url` 或 `ac_id` 配置有误，或认证页结构再次变更。请先在浏览器中打开认证页确认地址。

**登录成功但随即掉线**
`domain` 配置有误。电信为 `@dx`，移动为 `@cmcc`，校园网为 `@dx-uestc`。

**日志持续输出 offline**
`test_ip` 指向了不响应 ICMP 的地址，见「4.3 已知问题」第（2）条。

---

## 八、运行日志

日志由 `logger.py` 写入 `logs/` 目录，已随 `.gitignore` 忽略。日志内容与
`powershell` 分支一致，均为每次登录尝试的结果。

---

## 九、声明

### 许可

本项目采用 [MIT 许可证](LICENSE)。

本分支的认证实现（`BitSrunLogin/`）复制自
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
