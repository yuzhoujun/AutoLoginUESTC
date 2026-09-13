# UESTC 电子科技大学校园网认证

本仓库实现电子科技大学校园网（深澜 srun 认证）的自动登录与掉线自动重连，适用于
校园网有线接入及电信 / 移动寝室宽带的有线接入场景。

仓库提供**两个功能等价、可互换的实现**，分别位于 `python` 与 `powershell` 分支。
两个分支使用同一套认证协议，配置项语义、日志格式、重连行为一致，可按需选用其一。

`main` 分支（本页）仅包含项目说明与许可证，不包含代码。

---

## 一、分支说明

| 分支 | 实现 | 运行环境 | 适用场景 |
| --- | --- | --- | --- |
| [`python`](../../tree/python) | Python | Python 3.11+，无第三方依赖；Windows / Linux | 跨平台；便于阅读与修改协议实现 |
| [`powershell`](../../tree/powershell) | Windows PowerShell 5.1 | Windows 10 / 11（自带，无需安装） | Windows 环境下的零依赖部署 |

### 如何选择

- **Windows 环境、希望尽快部署** → 两个分支均可。`powershell` 分支无需安装 Python；
  `python` 分支需要 Python 3.11 及以上，但同样不需要安装任何第三方包。
- **需要 Linux** → 使用 `python` 分支。认证、常驻运行与开机自启（systemd）均已支持。
- **需要阅读或修改协议实现** → 两个分支均可。`python` 分支将加密算法与登录流程分
  目录组织，结构更便于对照；`powershell` 分支为同一协议的独立实现。

两个分支**都支持注册为开机自启的后台进程**：

| 分支 | Windows 计划任务 | Windows 服务 | Linux systemd | 管理入口 |
| --- | --- | --- | --- | --- |
| `python` | `python manage.py --install` | `python manage.py --install-service` | `sudo python manage.py --install` | `python manage.py` 交互菜单 |
| `powershell` | `.\install-task.ps1` | `.\install-service.ps1` | 不支持 | 双击 `autoConnectNetwork.bat` |

两者都以 Windows 计划任务为推荐方案（零依赖）。`python` 分支的命令行与交互菜单
均由 `manage.py` 提供，其 Windows 服务方式需要自行准备 nssm 或 WinSW 包装器，
与 `powershell` 分支的处理一致；Linux 上则使用 systemd，因此不需要批处理文件。

两个分支常驻运行时均为**前台进程**，关闭终端窗口即结束，因此只适合测试；长期无人
值守需要执行上面的注册命令。

### 实测环境

以下接入方式于 **2026-09-13** 在电子科技大学宿舍网环境实测：

```text
- 校园网有线接入 + 学号认证（主楼）
- 移动 / 电信寝室宽带有线接入 + 学号认证（硕丰 6、7、8 组团等插网线弹出认证页面的场景）
```

`powershell` 分支在上述环境下登录成功。`python` 分支面向相同的接入场景，但其实测
状态见下方说明。

> **`python` 分支的验证状态**：该分支的 HTTP 请求层近期由 `requests` 改为标准库
> `urllib`，目的是去掉唯一的第三方依赖。加密实现未受影响（有黄金向量逐字节比对），
> 但在新的请求层下**真实登录尚未重新实测**；自检、在线状态探测、重连逻辑、自启
> 注册与状态查询均已复验。首次使用建议先执行 `python manage.py --login` 确认。
> 详见该分支 README 的「四、验证」。

---

## 二、与参考仓库的关系

两个分支与参考仓库
[coffeehat/BIT-srun-login-script](https://github.com/coffeehat/BIT-srun-login-script)
的关系**并不相同**，此处分别说明。

### `python` 分支

该分支的认证实现（`BitSrunLogin/` 目录）与常驻循环（`manage.py` 中的
`always_login()`，对应参考仓库的 `always_online.py`）**来源于上述参考仓库**，并在此
基础上做了修改与扩展，主要包括：

- 修复本机 IP 的解析逻辑：新版认证页将 IP 置于 JavaScript 的 `var CONFIG = {...}`
  中，且登录页可能只是 `<meta http-equiv="refresh">` 跳转页，原实现在此情形下会
  抛出 `AttributeError: 'NoneType' object has no attribute 'group'`。
- 重写配置加载方式：由代码内硬编码配置改为读取独立的 `config.toml`，个人凭据不再
  进入仓库。
- 重写常驻循环：接入 `config.toml` 与日志模块，增加连续失败判定与探测间隔节流，
  并为该间隔补上下限（参考实现没有衰减，本项目早期版本衰减到 0 后曾退化为每秒一次
  的登录请求）。
- 在线探测由 `ping` 某个公共地址改为向认证服务器查询本机认证状态
  （`/cgi-bin/rad_user_info`），不再依赖 ICMP，也不再需要配置探测点。
- HTTP 请求改用标准库 `urllib`，去掉 `requests` 依赖。
- 其余文件（`logger.py`、`config.py`、`manage.py`、`selftest.py`、`autostart/`
  目录、配置文件模板等）为本项目新增。

因包含参考仓库的代码，该分支**保留了上游作者的版权声明**，详见「六、声明」。

### `powershell` 分支

该分支的**实现依据是深澜认证协议本身**，即公开的认证流程：取本机 IP、取 challenge
token、构造并加密 info、计算校验和、提交登录。

除该协议流程外，该分支**未使用参考仓库的代码**。全部 PowerShell 代码为独立编写，
函数划分、数据结构与错误处理均按 PowerShell 的惯例重新设计；参考仓库为 Python
实现，其代码未经复制或翻译。

该分支与参考实现之间唯一的直接关联是**验证方式**：为确保 XXTEA、HMAC-MD5、自定义
字母表 Base64 等步骤的输出与既有实现一致，该分支采集了一组黄金向量，通过
`-SelfTest` 做逐字节断言比对。这属于验证手段，不构成代码来源。

---

## 三、快速开始

### 使用 `powershell` 分支

```powershell
git clone -b powershell https://github.com/yuzhoujun/AutoLoginUESTC.git
cd AutoLoginUESTC
copy config.example.ini config.ini
```

编辑 `config.ini` 填写学号与密码，然后双击 `autoConnectNetwork.bat` 完成首次登录。
如需开机自动运行，以管理员身份执行 `.\install-task.ps1`。

配置项说明、自启方案、常见问题与加密自检方法，见
[`powershell` 分支的 README](../../tree/powershell#readme)。

### 使用 `python` 分支

```bash
git clone -b python https://github.com/yuzhoujun/AutoLoginUESTC.git
cd AutoLoginUESTC
cp config.example.toml config.toml      # Windows 上为 copy
```

只需要 Python 3.11 及以上，无需安装任何第三方包。编辑 `config.toml` 填写学号与密码，
然后执行：

```bash
python manage.py --self-test   # 加密实现自检（不联网）
python manage.py --login       # 登录一次，验证配置
python manage.py --daemon      # 前台常驻运行，掉线自动重连（关掉终端即停）
```

确认无误后注册开机自启。Windows（需管理员权限）：

```bash
python manage.py --install     # 注册计划任务
python manage.py --status      # 查看状态
python manage.py --uninstall   # 注销
```

Linux（需 root）：

```bash
sudo python manage.py --install    # 注册系统级 systemd unit
python manage.py --status
sudo python manage.py --uninstall
```

不带参数执行 `python manage.py` 会进入交互菜单，上述操作均可通过菜单完成。完整
说明见 [`python` 分支的 README](../../tree/python#readme)。

> 直接切换分支亦可：`git clone` 后执行 `git checkout python`（或 `powershell`）与
> `git clone -b <分支>` 等价。两个分支的代码与配置文件互不影响，可分别检出。

---

## 四、认证流程

两个分支实现的是同一套流程，共六步：

```text
1. 取本机 IP      GET {portal}/                 从页面中解析 ip
2. 取 token       GET /cgi-bin/get_challenge
3. 拼接 info      {"username":...,"password":...,"ip":...,"acid":...,"enc_ver":"srun_bx1"}
4. 加密           info     = "{SRBX1}" + 自定义字母表 Base64(XXTEA(info, token))
                  password = "{MD5}"   + HMAC-MD5(key=token, msg=password)
5. 计算校验和     SHA1 依次拼接 token 与上述各字段后哈希
6. 提交登录       GET /cgi-bin/srun_portal?action=login&...
```

实现时需注意的三点，两个分支均已处理：

1. **密码字段不是普通 MD5**，而是 `HMAC-MD5`，key 为 token、message 为密码明文。
   `certutil` 等工具只能计算普通哈希，无法得到正确结果。
2. **Base64 使用自定义字母表**
   （`LVoJPiCN2R8G90yg+hmFHuacZ1OWMnrsSTXkYpUq/3dlbfKwv6xztjI7DeBE45QA`），并非标准
   Base64。例如编码 `132456` 得 `9F9x0JHI`，标准 Base64 则为 `MTMyNDU2`。
3. **本机 IP 的获取方式已变更**：新版认证页将其置于 JavaScript 的 `var CONFIG = {...}`
   中，旧版页面才是隐藏 input；且登录页常为 `<meta http-equiv="refresh">` 跳转页，
   需先跟随跳转到达真实认证页 —— `urllib` 与 `Invoke-WebRequest` 均不会自动跟随。

---

## 五、配置文件

两个分支各自使用一份独立的个人配置文件存放学号与密码：

| 分支 | 个人配置（不提交） | 模板（提交） |
| --- | --- | --- |
| `python` | `config.toml` | `config.example.toml` |
| `powershell` | `config.ini` | `config.example.ini` |

两份个人配置文件均已在 `.gitignore` 中忽略，不会进入仓库，可填写真实密码。提交前建议
执行 `git status` 确认其未被纳入暂存区。

---

## 六、声明

### 许可

本项目采用 [MIT 许可证](LICENSE)。

`python` 分支包含来自
[coffeehat/BIT-srun-login-script](https://github.com/coffeehat/BIT-srun-login-script)
的代码，因此 `LICENSE` 中保留了上游作者的版权声明
（`Copyright (c) 2020 coffeehat`）。这是 MIT 许可证的要求，请勿删除。其后一行是本
项目的版权声明。

### 参考

- [coffeehat/BIT-srun-login-script](https://github.com/coffeehat/BIT-srun-login-script)
  —— 深澜认证流程的公开实现，本项目的协议依据。该仓库另提供支持 OpenWrt 的 Go 版本。
- 深澜认证被多所高校采用，GitHub 上存在较多同类实现，遇到问题时可供对照参考。

### 免责声明

本项目仅供个人学习与自用。请仅在自己的账号上使用，不得用于批量登录他人账号或任何
未经授权的用途。账号密码仅保存在本地被 gitignore 忽略的配置文件中，不会上传至任何
服务器；但若因手动提交导致泄露，责任由使用者自负，提交前请确认 `git status` 的输出。
