# UESTC 电子科技大学网络认证脚本（纯 PowerShell 版）

自动登录校园网 / 寝室宽带，掉线自动重连。**不需要装 Python**，Windows 自带的
PowerShell 就能跑。配置只写一个 `config.ini`，不用碰代码。

> 这个分支是 **PowerShell 原生实现**，Python 版在 [`python` 分支](../../tree/python)，
> 项目总说明和两个版本的对比在 [`main` 分支](../../tree/main)。
> 两个版本功能等价、可以互换，按喜好挑一个用。

---

## 搞这干啥？

- 学校的电信宽带自动掉线太频繁了，移动的稍好一点但也不行（尊贵的移动还屏蔽了游戏串流软件，真是谢谢你）
- 校园网很稳定，很少掉线。但是如果再出现封在家里一个月没法回学校的情况，那就得想办法让电脑一直在线了，不然没法给老板打工。

支持登录以下类型的网络（我都试过的）：

```text
- 校园网有线接入 + 学号认证（主楼，至今可用）
- 移动、电信寝室宽带有线接入 + 学号认证（硕丰 6、7、8 组团那种插网线直接弹出认证页面的，至今可用）
```

---

## 快速开始

### 1. 不需要装任何东西

Windows 10 / 11 自带的 Windows PowerShell 5.1 就够了。加密用的是 .NET 的
`System.Security.Cryptography`，HTTP 用的是 `Invoke-WebRequest`，全是系统内置。

### 2. 写自己的配置

仓库里只有一份模板 `config.example.ini`。把它复制成 `config.ini`，填上学号和密码：

```bat
copy config.example.ini config.ini
```

`config.ini` 已经被 `.gitignore` 忽略，**不会被提交到仓库**，可以放心写真实密码。

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

> **注释只能单独占一行。** 不要写成 `password = abc  ; 我的密码` 这种行尾注释 ——
> 密码里可能包含 `;` 或 `#`，行尾注释会把密码截断，导致登录莫名失败。所以这个
> ini 解析器故意不处理行尾注释。

### 3. 试一下能不能登录

先在浏览器里手动注销、断开网络，然后双击 `autoConnectNetwork.bat`，或者命令行跑：

```powershell
powershell -ExecutionPolicy Bypass -File .\uestc-login.ps1 -Once
```

看到 `The loggin result is: ok` 就说明配置没问题。

### 4. 挂着自动重连

```powershell
powershell -ExecutionPolicy Bypass -File .\uestc-login.ps1 -Daemon
```

它会定时 ping `test_ip`，发现断网就自动重新登录，断线重连不用管。日志写在
`logs\uestc-login.log`。

想开机就自动跑、平时完全不用管，看下面「开机自启」一节（推荐注册成计划任务）。

---

## 运行模式

| 参数                   | 作用                                                 |
| ---------------------- | ---------------------------------------------------- |
| `-Once`              | 登录一次就退出，用来验证配置（默认）                 |
| `-Daemon`            | 常驻，掉线自动重连                                   |
| `-SelfTest`          | 跑加密自检，校验移植是否和 Python 参考实现逐字节一致 |
| `-ConfigPath <路径>` | 用指定的配置文件，默认脚本同目录的`config.ini`     |

`-SelfTest` 用的黄金向量是从 Python 参考实现里实测采集的，包括自定义字母表
Base64、HMAC-MD5、SHA1 和 XXTEA（srun 的 `xencode`）。这些加密步骤必须逐字节
一致，差一个 bit 登录就会失败，所以自检不过就别往下走了：

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

全部通过，加密移植与 Python 参考实现逐字节一致。
```

---

## 配置项说明

| 字段                   | 说明                                                                                |
| ---------------------- | ----------------------------------------------------------------------------------- |
| `account.username`   | 学号                                                                                |
| `account.password`   | 教务处密码                                                                          |
| `account.domain`     | 网络提供商：电信`@dx`、移动 `@cmcc`、校园网 `@dx-uestc`                       |
| `portal.url`         | 认证页地址：寝室公寓`http://10.253.0.235`，主楼有线校园网 `http://10.253.0.237` |
| `portal.ac_id`       | 认证页地址里的`ac_id` 参数：寝室公寓 `3`，主楼有线 `1`                        |
| `monitor.test_ip`    | 用来判断当前是否联网的 IP，**ping 得通**才算在线                              |
| `monitor.delay`      | 掉线检测间隔（秒），默认 16                                                         |
| `monitor.max_failed` | 连续 ping 失败多少次才认为断网，默认 3                                              |

`url` 和 `ac_id` 怎么确认？把 `url` 粘进浏览器，认证页地址栏里长得像
`http://10.253.0.235/srun_portal_pc?ac_id=3&theme=pro`，那个 `ac_id` 就是。

### `test_ip` 别随便填

这个探测点**必须真的回 ICMP**。很多公共 DNS 是屏蔽 ping 的，一旦探测点不通，
程序就会一直以为你断网（哪怕你其实在线），然后不停地重登。

实测 **`114.114.114.114` 在电子科大宿舍网上是 100% 丢包**，所以模板里默认换成了
`223.5.5.5`（阿里 DNS）。`119.29.29.29`（腾讯 DNS）也可以。要是想确认某个 IP 行不行，
自己先 `ping 一下`：

```bat
ping -n 3 223.5.5.5
```

看到 `Lost = 0 (0% loss)` 才能拿来当探测点。

---

## 双击运行

`autoConnectNetwork.bat` 是个双击启动器，默认 `-Once`（登录一次就退出）。
想要常驻重连，把里面的 `-Once` 改成 `-Daemon`。

> **这个 bat 是纯 ASCII 的，故意的。** 在 GBK 代码页的控制台里，cmd.exe 解析
> 带中文的 UTF-8 `.bat` 会乱码到把中文片段当命令执行（`'不到' 不是内部或外部命令`
> 这种），所以中文注释全部放在 README 里，不写进 bat。

如果双击提示 `'powershell' 不是内部或外部命令`（极少见，一般是 PATH 被改坏了），
打开 bat，把下面这一行行首的 `rem` 删掉：

```bat
rem set "PS=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
```

---

## 开机自启

给了两种方案，**推荐第一个**。

### 方案 A：计划任务（推荐，零依赖）

```powershell
# 需要「以管理员身份运行」的 PowerShell
.\install-task.ps1
```

它会注册一个叫 `UESTC-AutoLogin` 的计划任务：

- **开机触发**，延迟 30 秒等网络栈就绪
- 以 **SYSTEM** 身份运行 —— 不依赖桌面会话，也不需要在任务里存密码
  （认证是按机器 IP 做的，跟谁登录无关）
- 挂了自动重启（1 分钟间隔，无限次）
- 不限运行时长

卸载：

```powershell
.\uninstall.ps1
```

### 方案 B：Windows 服务（需要 nssm 或 WinSW）

```powershell
.\install-service.ps1
```

**为什么不能直接 `sc create`？** Windows 服务必须实现 SCM 的 `ServiceMain` /
状态上报协议，而 PowerShell 脚本不是服务宿主程序，所以 `sc create` 指向
`powershell.exe` 是起不来的，必须用一个服务包装器。

`install-service.ps1` 只负责**检测**本机有没有 `nssm.exe` / `WinSW.exe`，
**不会自动下载第三方二进制**。没有的话它会打印下载地址然后退出。装好之后：

```text
方案 A —— nssm（推荐，最简单）
  1. 从 https://nssm.cc/download 下载，解压出 win64\nssm.exe
  2. 把 nssm.exe 放到本目录
  3. 重新运行 .\install-service.ps1
```

`uninstall.ps1` 两种都能卸，重复跑也没事（幂等）。

> 计划任务在**睡眠 / 休眠期间不执行**。要真正做到 7×24 在线，得在
> 「电源选项」里把机器设成不睡眠，或者在任务属性里勾上「唤醒计算机运行此任务」。

---

## 目录结构

```text
AutoLoginUESTC/
├── config.example.ini    # 配置模板（提交到仓库）
├── config.ini            # 你的个人配置（已 gitignore，不提交）
├── uestc-login.ps1       # 核心：读配置 + 加密 + 登录 + 守护循环
├── autoConnectNetwork.bat# 双击启动器（纯 ASCII）
├── install-task.ps1      # 注册计划任务（推荐）
├── install-service.ps1   # 注册 Windows 服务（需要 nssm/WinSW）
├── uninstall.ps1         # 卸载上面两者
└── logs/                 # 日志
```

---

## 常见问题

**提示「找不到配置文件 ...\config.ini」**
忘了复制模板。执行 `copy config.example.ini config.ini` 再填上账号。

**`-SelfTest` 有 FAIL**
加密移植出问题了，别往下走。重点检查 PowerShell 5.1 的 32 位整数陷阱：
`0xFFFFFFFF` 会被解析成 Int32 的 `-1`，`[int64]0xFFFFFFFF` **同样是** `-1`，
只有 `0xFFFFFFFFL` 才是 `4294967295`。XXTEA 每一步掩码都得用它。

**登录成功但日志里一直刷「检测到断网，尝试重新登录」**
`test_ip` 填了个不回 ICMP 的地址，程序误判你断网了。换成 `223.5.5.5` 试试，
判据见上面「`test_ip` 别随便填」。

**`Failed to resolve IP` / `Cannot find local ip in login page html`**
认证页地址填错了（`url` / `ac_id` 不对），或者学校把深澜认证页又改版了。
先用浏览器打开认证页确认地址栏。

**登录成功但立刻又掉线**
`domain` 填错了。电信 `@dx`、移动 `@cmcc`、校园网 `@dx-uestc`，换一个试试。

**想改自己电脑上的登录逻辑（`uestc-login.ps1`）**
改完保存时**必须存成「UTF-8 带 BOM」**。PowerShell 5.1 读不带 BOM 的 `.ps1`
会按 ANSI 解码，文件里的中文注释就会乱掉，甚至报语法错误。

---

### 抄的！抄的！抄的！

- 楼主入学的时候深澜软件的网络认证页面已经经过混淆了，还好 GitHub 有大佬之前写好的登录流程相关代码，
  所以就完全照着抄了这个 [https://github.com/coffeehat/BIT-srun-login-script](https://github.com/coffeehat/BIT-srun-login-script)
- 好多学校都是这套登录逻辑，所以 GitHub 脚本很多，上边这个链接里也有支持 OpenWrt 的 go 版本。
- 这个分支是把上面那套 Python 实现（[`python` 分支](../../tree/python)）原样移植成 PowerShell，
  加密部分用 Python 版采集的黄金向量做了逐字节校验 —— 协议是抄的，移植是自己写的。
