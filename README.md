# UESTC 电子科技大学校园网认证 —— PowerShell 实现

本分支使用 Windows 自带的 Windows PowerShell 5.1 实现电子科技大学校园网（深澜 srun
认证）的自动登录与掉线重连。**不依赖 Python，也不需要安装任何第三方组件或运行时。**

配置通过同目录下的 `config.ini` 提供，无需修改代码。

> 本分支为 PowerShell 原生实现，Python 版见 [`python` 分支](../../tree/python)，
> 项目总说明与两个版本的对比见 [`main` 分支](../../tree/main)。
> 两个版本功能等价，可任选其一。

---

## 一、与参考仓库的关系

本分支的**实现依据是深澜（srun）认证协议本身**，即公开的认证流程：取本机 IP、取
challenge token、构造并加密 info、计算校验和、提交登录。

除该协议流程外，本分支**未使用参考仓库的代码**：全部 PowerShell 代码为独立编写，
函数划分、数据结构与错误处理均按 PowerShell 的习惯重新设计。参考仓库为 Python
实现，其代码未经复制或翻译。

唯一与参考实现存在直接关联的是**加密部分的验证方式**：为确保 XXTEA、HMAC-MD5、
自定义字母表 Base64 等步骤与既有实现逐字节一致，本分支从参考实现采集了一组黄金
向量，通过 `-SelfTest` 做断言比对（详见「四、验证」）。这是验证手段，不是代码来源。

参考仓库与致谢名单见 [`main` 分支的说明](../../tree/main)。

---

## 二、环境要求

| 项目 | 要求 |
| --- | --- |
| 操作系统 | Windows 10 / 11 |
| 运行时 | Windows PowerShell 5.1（系统自带） |
| 第三方依赖 | 无 |

加密使用 .NET 的 `System.Security.Cryptography`，HTTP 请求使用内置的
`Invoke-WebRequest`，均为系统组件。

> 本实现针对 **Windows PowerShell 5.1（Desktop 版）** 编写。PowerShell 7
> 未做验证；脚本中若干写法（如 `-UseBasicParsing`、数组与 `$null` 比较）是为
> 5.1 的行为确定的。

---

## 三、使用方法

### 3.1 获取代码

```powershell
git clone -b powershell https://github.com/yuzhoujun/AutoLoginUESTC.git
cd AutoLoginUESTC
```

### 3.2 创建个人配置

仓库中只提供模板 `config.example.ini`。将其复制为 `config.ini`：

```bat
copy config.example.ini config.ini
```

`config.ini` 已在 `.gitignore` 中忽略，不会被提交到仓库，可填写真实密码。

```ini
[account]
username = 202912272625
password = your_password
domain   = @dx

[portal]
url   = http://10.253.0.235
ac_id = 3

[monitor]
test_ip    = 223.5.5.5
delay      = 16
max_failed = 3
```

> **注释必须单独占一行。** 不支持 `password = abc  ; 说明` 这类行尾注释。原因是
> 密码中可能包含 `;` 或 `#`，按行尾注释截断会导致密码被静默改错、登录失败。该
> 限制是解析器有意为之，见 `Read-UestcConfig` 的注释。

### 3.3 验证配置

在浏览器中手动注销、断开网络，然后双击 `autoConnectNetwork.bat`，或在命令行执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\uestc-login.ps1 -Once
```

输出 `The loggin result is: ok` 表示配置正确。

> `-Once` 会打印认证服务器返回的完整 JSON，其中包含 `access_token`。该字段是本次
> 会话的临时凭证，请勿将这段输出粘贴到公开场合。

### 3.4 常驻运行

```powershell
powershell -ExecutionPolicy Bypass -File .\uestc-login.ps1 -Daemon
```

程序按 `delay` 间隔探测 `test_ip`，连续失败 `max_failed` 次即判定断网并重新登录。
日志写入 `logs\uestc-login.log`。

若需开机自动运行、无需人工干预，见「六、开机自启」。

---

## 四、验证

### 4.1 加密自检

```powershell
.\uestc-login.ps1 -SelfTest
```

该命令不联网，仅校验加密函数：

```text
SrunBase64:
  [OK]   base64("132456")
HmacMd5 / Sha1:
  [OK]   hmac_md5("pw")
  [OK]   sha1("hello")
XEncode (XXTEA):
  [OK]   xencode 长度
  [OK]   xencode 前12字节
  [OK]   xencode + base64

全部通过：加密实现与参考实现的输出逐字节一致。
```

黄金向量的输入为：

```text
key = abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789
msg = {"username":"1234567890@dx","password":"pw","ip":"10.0.0.1","acid":"3","enc_ver":"srun_bx1"}
```

其中 `base64("132456")` 的期望结果是 `9F9x0JHI`，而非标准 Base64 的 `MTMyNDU2`，
用于确认自定义字母表实现正确。

### 4.2 实测结果

以下结果均于 **2026-09-13** 在电子科技大学宿舍网环境实测：

| 项目 | 结果 |
| --- | --- |
| `-SelfTest` | 6 / 6 向量通过 |
| `-Once` 实际登录 | 返回 `"error":"ok"` |
| `autoConnectNetwork.bat` | 退出码 0 |
| 计划任务注册 → 启动 → 卸载 | 通过，守护进程可被完整清理 |
| 掉线重连节流 | 重试间隔稳定为 19 秒（修复前为 1 秒/次，详见 4.3） |

支持的接入方式（2026-09-13 验证）：

```text
- 校园网有线接入 + 学号认证（主楼）
- 移动 / 电信寝室宽带有线接入 + 学号认证（硕丰 6、7、8 组团等插网线弹出认证页面的场景）
```

### 4.3 已修复的缺陷

移植过程中定位并修复了两个缺陷。二者来源不同，且两个分支现已各自修复
（2026-09-13）：

#### （1）监控循环的重试间隔无下限

Python 版 `always_online.py` 中为 `delay = max(0., delay / 2)`，衰减没有下限，且
登录尝试后不复位。当探测点持续不可达时 `delay` 会衰减到 0，循环失去等待，形成
每秒一次的登录请求。

该逻辑并非来自参考仓库：参考仓库的同名脚本只有固定间隔，没有衰减，是本项目在
扩展该脚本时引入的。

本分支的处理：为衰减设置 2 秒下限，并在每次登录尝试后重新计数、间隔复位到
`delay`。实测重试间隔由 1 秒/次变为稳定的 19 秒/次。

#### （2）默认探测点不可达

模板原默认值 `114.114.114.114` 在电子科技大学宿舍网 **100% 丢包**，导致探测恒为
失败。程序会持续判定断网并反复重登，即使网络实际正常。

该默认值继承自参考实现（其 `always_online.py` 中为 `testip = "114.114.114.114"`）。
现已将该值与代码中的兜底默认值一并改为 `223.5.5.5`。

`test_ip` 必须是一个**确实响应 ICMP 的地址**。选用前请自行确认：

```bat
ping -n 3 223.5.5.5
```

输出 `Lost = 0 (0% loss)` 方可使用。备选：`223.5.5.5`（阿里 DNS）、
`119.29.29.29`（腾讯 DNS），均于 2026-09-13 验证可达。

> `python` 分支已于 2026-09-13 一并修复上述两个缺陷，两分支现行为一致。

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

---

## 六、开机自启

提供两种方案。**推荐方案 A**，无需任何第三方文件。

### 方案 A：计划任务（推荐）

以管理员身份运行 PowerShell，执行：

```powershell
.\install-task.ps1
```

注册名为 `UESTC-AutoLogin` 的计划任务，其配置为：

- 触发方式：开机，延迟 30 秒（等待网络栈就绪）
- 运行身份：`SYSTEM`，不依赖用户桌面会话，无需在任务中保存账户密码
  （认证按机器 IP 进行，与会话无关）
- 失败重启：间隔 1 分钟，次数不限
- 运行时长限制：无

卸载：

```powershell
.\uninstall.ps1
```

### 方案 B：Windows 服务

```powershell
.\install-service.ps1
```

**为什么不能直接用 `sc create`？** Windows 服务必须实现 SCM 的 `ServiceMain` 与
状态上报协议，而 PowerShell 脚本并非服务宿主程序，因此 `sc create` 直接指向
`powershell.exe` 无法启动。标准做法是借助服务包装器。

本脚本只**检测**本机是否已安装 `nssm.exe` 或 `WinSW.exe`，**不会自动下载第三方
二进制文件**。若未检测到，脚本会打印下载方式并退出：

```text
方案 A —— nssm（推荐）
  1. 从 https://nssm.cc/download 下载，解压出 win64\nssm.exe
  2. 将 nssm.exe 放入本目录
  3. 重新运行 .\install-service.ps1
```

`uninstall.ps1` 对两种方案均适用，且可重复执行（幂等），会一并清理残留的守护进程。

> 计划任务在系统睡眠 / 休眠期间不会执行。若需 7×24 在线，请在「电源选项」中关闭
> 睡眠，或在任务属性中启用「唤醒计算机运行此任务」。

---

## 七、代码说明

```text
AutoLoginUESTC/
├── config.example.ini     配置模板（提交至仓库）
├── config.ini             个人配置（已 gitignore，不提交）
├── uestc-login.ps1        核心实现
├── autoConnectNetwork.bat 双击启动器
├── install-task.ps1       注册计划任务
├── install-service.ps1    注册 Windows 服务
├── uninstall.ps1          卸载计划任务与 Windows 服务
└── logs/                  运行日志（已 gitignore）
```

### `uestc-login.ps1`

单一入口，按以下顺序组织：

| 区块 | 函数 | 说明 |
| --- | --- | --- |
| 参数 | `param(...)` | `-Once` / `-Daemon` / `-SelfTest` / `-ConfigPath` |
| 常量 | — | 自定义 Base64 字母表、32 位掩码、协议固定参数、自检黄金向量 |
| 加密 | `Get-SrunBase64` | 自定义字母表的 Base64 编码 |
| 加密 | `ConvertTo-SrunWords` | 4 字节小端打包为 32 位字，可选追加原始长度 |
| 加密 | `Get-XEncode` | XXTEA 变体，加密 info 字符串 |
| 加密 | `Get-HmacMd5` | HMAC-MD5，key 为 token，message 为密码 |
| 加密 | `Get-Sha1` | SHA1，用于校验和 |
| 配置 | `Read-UestcConfig` | 解析 `config.ini`，校验必填项，补默认值 |
| 网络 | `Invoke-HttpGet` | 带 `-UseBasicParsing` 的 GET，异常时读取错误响应体 |
| 流程 | `Get-LoginIp` | 解析本机 IP |
| 流程 | `Get-ChallengeToken` | 获取 challenge token |
| 流程 | `New-LoginInfo` | 拼接待加密的 info 字符串 |
| 流程 | `Invoke-SrunLogin` | 完整的六步登录流程 |
| 运行 | `Start-Monitor` | 守护循环：探测、判定、重登、节流 |
| 运行 | `Invoke-SelfTest` | 黄金向量自检 |

### 认证流程

```text
1. 取本机 IP      GET {portal}/         从页面中解析 ip
2. 取 token       GET /cgi-bin/get_challenge
3. 拼接 info      {"username":...,"enc_ver":"srun_bx1"}
4. 加密           info     = "{SRBX1}" + 自定义Base64(XXTEA(info, token))
                  password = "{MD5}"   + HMAC-MD5(key=token, msg=password)
5. 计算校验和     SHA1 依次拼接 token 与上述各字段后哈希
6. 提交登录       GET /cgi-bin/srun_portal?action=login&...
```

实现中需要注意的三点（代码内均有对应注释）：

1. **密码不是普通 MD5**，而是 `HMAC-MD5`，key 为 token、message 为密码。
2. **Base64 使用自定义字母表**（`LVoJPiCN2R8G90yg+hmFHuacZ1OWMnrsSTXkYpUq/3dlbfKwv6xztjI7DeBE45QA`），
   并非标准 Base64。
3. **本机 IP 的获取方式已变更**：新版认证页将其置于 JavaScript 的 `var CONFIG = {...}`
   中，旧版页面才是隐藏 input。此外登录页常为 `<meta http-equiv="refresh">` 跳转页，
   需先跟随跳转到达真实认证页 —— `Invoke-WebRequest` 与 Python 的 `requests` 均不会
   自动跟随该跳转。

### PowerShell 5.1 的注意事项

代码中已就地注释，此处汇总供修改时参考：

| 问题 | 说明 |
| --- | --- |
| `0xFFFFFFFF` 字面量 | PS 5.1 将其解析为 Int32 的 `-1`；`[int64]0xFFFFFFFF` 同样为 `-1`。只有 `0xFFFFFFFFL` 才是 `4294967295`。XXTEA 每一步掩码都必须使用它，否则中间结果会溢出为浮点数 |
| `-shr` 对负数 | 执行算术右移并补符号位，因此所有中间值都需用掩码收敛回 32 位无符号范围 |
| `Invoke-WebRequest` | 必须加 `-UseBasicParsing`，否则依赖 IE 引擎首次配置 |
| 响应解码 | 认证页可能只在 HTML 的 meta 中声明 UTF-8，HTTP 头无 charset，需按 UTF-8 手动解码而非依赖 `.Content` |
| 脚本文件编码 | `.ps1` 含中文时**必须保存为「UTF-8 带 BOM」**，否则 PS 5.1 按 ANSI 解码，中文注释会错乱甚至导致语法错误 |
| `.bat` 文件编码 | 必须为**纯 ASCII**。在 GBK 代码页的控制台中，cmd.exe 解析含中文的 UTF-8 `.bat` 会将中文片段当作命令执行，故中文说明不写入 bat |

---

## 八、常见问题

**提示「找不到配置文件 ...\config.ini」**
未复制模板。执行 `copy config.example.ini config.ini` 后填写账号信息。

**`-SelfTest` 出现 FAIL**
加密实现存在问题，不建议继续使用。首先检查 32 位整数陷阱（见「PowerShell 5.1 的
注意事项」中关于 `0xFFFFFFFFL` 的说明）。

**登录成功，但日志持续输出「检测到断网，尝试重新登录」**
`test_ip` 指向了一个不响应 ICMP 的地址，导致误判断网。改用 `223.5.5.5` 后复测。

**`Failed to resolve IP` / `Cannot find local ip in login page html`**
`url` 或 `ac_id` 配置有误，或认证页结构再次变更。请先在浏览器中打开认证页确认地址。

**登录成功但随即掉线**
`domain` 配置有误。电信为 `@dx`，移动为 `@cmcc`，校园网为 `@dx-uestc`。

**修改 `uestc-login.ps1` 后出现乱码或语法错误**
保存时未使用「UTF-8 带 BOM」。见「PowerShell 5.1 的注意事项」。

---

## 九、声明

### 许可

本项目采用 [MIT 许可证](LICENSE)。登录流程的实现参考了
[coffeehat/BIT-srun-login-script](https://github.com/coffeehat/BIT-srun-login-script)，
因此 `LICENSE` 中保留了上游作者的版权声明（`Copyright (c) 2020 coffeehat`）。
这是 MIT 许可证的要求，请勿删除。

### 参考

- [coffeehat/BIT-srun-login-script](https://github.com/coffeehat/BIT-srun-login-script)
  —— 深澜认证流程的公开实现，本项目的协议依据。该仓库另提供支持 OpenWrt 的 Go 版本。
- 深澜认证被多所高校采用，GitHub 上有较多同类实现，遇到问题时可供对照参考。

### 免责声明

本项目仅供个人学习与自用。请仅在自己的账号上使用，不得用于批量登录他人账号或任何
未经授权的用途。账号密码仅保存在本地被 gitignore 忽略的配置文件中，不会上传至任何
服务器；但若因手动提交导致泄露，责任由使用者自负，提交前请确认 `git status` 的输出。
