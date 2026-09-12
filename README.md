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
| [`python`](../../tree/python) | Python | Python 3.11+、`requests` | 跨平台；便于阅读与修改协议实现 |
| [`powershell`](../../tree/powershell) | Windows PowerShell 5.1 | Windows 10 / 11（自带，无需安装） | Windows 环境下的零依赖部署 |

### 如何选择

- **Windows 环境、希望尽快部署** → 使用 `powershell` 分支。无需安装 Python 或任何
  第三方组件，双击批处理文件即可运行。
- **需要跨平台，或使用 Linux / macOS / 路由器** → 使用 `python` 分支。
- **需要阅读或修改协议实现** → 两个分支均可。`python` 分支将加密算法与登录流程分
  目录组织，结构更便于对照；`powershell` 分支为同一协议的独立实现。

两个分支**都支持注册为开机自启的后台进程**，均提供计划任务与 Windows 服务两种
方式，并且都以计划任务为推荐方案（零依赖）：

| 分支 | 计划任务 | Windows 服务 | 管理入口 |
| --- | --- | --- | --- |
| `python` | `python manage.py install` | `python manage.py install-service` | `autoConnectNetwork.bat` 菜单 |
| `powershell` | `.\install-task.ps1` | `.\install-service.ps1` | `autoConnectNetwork.bat` |

两个分支的常驻脚本均为**前台进程**，关闭终端窗口即结束，因此只适合测试；长期无人
值守需要执行上面的注册命令。

### 实测环境

以下结果于 **2026-09-13** 在电子科技大学宿舍网环境实测：

```text
- 校园网有线接入 + 学号认证（主楼）
- 移动 / 电信寝室宽带有线接入 + 学号认证（硕丰 6、7、8 组团等插网线弹出认证页面的场景）
```

两个分支在该环境下均登录成功。

---

## 二、与参考仓库的关系

两个分支与参考仓库
[coffeehat/BIT-srun-login-script](https://github.com/coffeehat/BIT-srun-login-script)
的关系**并不相同**，此处分别说明。

### `python` 分支

该分支的认证实现（`BitSrunLogin/` 目录）与常驻脚本（`always_online.py`）**来源于上述
参考仓库**，并在此基础上做了修改与扩展，主要包括：

- 修复本机 IP 的解析逻辑：新版认证页将 IP 置于 JavaScript 的 `var CONFIG = {...}`
  中，且登录页可能只是 `<meta http-equiv="refresh">` 跳转页，原实现在此情形下会
  抛出 `AttributeError: 'NoneType' object has no attribute 'group'`。
- 重写配置加载方式：由代码内硬编码配置改为读取独立的 `config.toml`，个人凭据不再
  进入仓库。
- 重写常驻脚本：接入 `config.toml` 与日志模块，增加连续失败判定与探测间隔节流，
  `ping` 参数按操作系统选择（参考实现固定使用 Linux 语法的 `-c`）。
- 其余文件（`logger.py`、`config.py`、`manage.py`、`selftest.py`、
  `autoConnectNetwork.bat`、配置文件模板等）为本项目新增。

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
pip install requests
cp config.example.toml config.toml
```

编辑 `config.toml` 填写学号与密码，然后执行：

```bash
python selftest.py       # 加密实现自检（不联网）
python login_once.py     # 登录一次，验证配置
python always_online.py  # 前台常驻运行，掉线自动重连（关掉终端即停）
```

确认无误后注册开机自启（需管理员权限）：

```bash
python manage.py install   # 注册计划任务
python manage.py status    # 查看状态
python manage.py uninstall # 注销
```

也可以直接双击 `autoConnectNetwork.bat`，通过交互菜单完成上述操作。完整说明见
[`python` 分支的 README](../../tree/python#readme)。

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
   需先跟随跳转到达真实认证页 —— `requests` 与 `Invoke-WebRequest` 均不会自动跟随。

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
项目对自身修改部分的声明。

### 参考

- [coffeehat/BIT-srun-login-script](https://github.com/coffeehat/BIT-srun-login-script)
  —— 深澜认证流程的公开实现，本项目的协议依据。该仓库另提供支持 OpenWrt 的 Go 版本。
- 深澜认证被多所高校采用，GitHub 上存在较多同类实现，遇到问题时可供对照参考。

### 免责声明

本项目仅供个人学习与自用。请仅在自己的账号上使用，不得用于批量登录他人账号或任何
未经授权的用途。账号密码仅保存在本地被 gitignore 忽略的配置文件中，不会上传至任何
服务器；但若因手动提交导致泄露，责任由使用者自负，提交前请确认 `git status` 的输出。
