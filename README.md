# UESTC 电子科技大学网络认证脚本

自动登录校园网 / 寝室宽带，掉线自动重连。这个仓库提供**两个功能等价、可互换的实现**，
分别放在两个分支上，挑一个用就行。

| 分支 | 实现 | 需要装什么 | 说明 |
| --- | --- | --- | --- |
| [`python`](../../tree/python) | Python | Python 3.11+ 和 `requests` | 最早写的版本，跨平台，也方便自己改协议 |
| [`powershell`](../../tree/powershell) | Windows PowerShell 5.1 | **什么都不用装** | 把 Python 版原样移植过来的，Windows 上用这个最省事 |

两个分支都实现了同一套深澜（srun）认证协议，配置项、日志、掉线重连的行为一致。
`main`（就是本页）只放这份总说明，不放代码。

---

## 我该选哪个？

- **只想赶紧用上** → `powershell` 分支。Windows 10 / 11 自带的 PowerShell 就够，
  双击一个 `.bat` 就能跑，不用配环境、不用装依赖。
- **装了 Python，或者想跑在 Linux / macOS / 路由器上** → `python` 分支。
- **想读协议实现** → 两个都行。`python` 分支更好读（`BitSrunLogin/` 里
  加密和登录流程分得很清楚），`powershell` 分支是它的逐行对照移植。

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

### 用 `powershell` 分支（推荐，零依赖）

```powershell
git clone -b powershell https://github.com/yuzhoujun/AutoLoginUESTC.git
cd AutoLoginUESTC
copy config.example.ini config.ini
```

编辑 `config.ini` 填上学号和密码，然后双击 `autoConnectNetwork.bat`。
想开机自启、长期挂着，用管理员身份运行 `.\install-task.ps1`。

完整说明（配置项、自启、常见问题、加密自检）见
[`powershell` 分支的 README](../../tree/powershell#readme)。

### 用 `python` 分支

```bash
git clone -b python https://github.com/yuzhoujun/AutoLoginUESTC.git
cd AutoLoginUESTC
pip install requests
cp config.example.toml config.toml
```

编辑 `config.toml` 填上学号和密码，然后 `python login_once.py` 验证能不能登录，
`python always_online.py` 挂着自动重连。

完整说明见 [`python` 分支的 README](../../tree/python#readme)。

> 就像 `main` 分支切换过去也行：
> `git clone -b python <url>` 等价于 `git clone <url>` 之后 `git checkout python`。
> 两个分支的代码和配置文件互不影响，可以同时 clone 两份。

---

## 认证流程（两个分支都一样）

学校用的是深澜（srun）那套认证。整个登录就六步：

```text
1. 取本机 IP      GET {portal}/  → 页面里拿 ip
2. 取 challenge   GET /cgi-bin/get_challenge  → token
3. 拼 info        {"username":...,"password":...,"ip":...,"acid":...,"enc_ver":"srun_bx1"}
4. 加密           info = "{SRBX1}" + 自定义字母表 Base64(XXTEA(info, token))
                  password = "{MD5}" + HMAC-MD5(key=token, msg=password)
5. 算校验和       SHA1 把 token 和上面各字段依次拼接后哈希
6. 提交           GET /cgi-bin/srun_portal?action=login&...
```

几个容易踩的坑，两个分支都处理了：

- 密码**不是**普通 MD5，是 `HMAC-MD5`，key 是 token、message 是密码。用 `certutil` 算的不对。
- Base64 用的是**自定义字母表**（`LVoJPiCN2R8G90yg+hmFHuacZ1OWMnrsSTXkYpUq/3dlbfKwv6xztjI7DeBE45QA`），
  不是标准 Base64。
- 认证页地址栏里的 `ip` 现在藏在 JS 的 `var CONFIG = {...}` 里，老页面才是隐藏 input；
  而且登录页常常只是个 `<meta http-equiv="refresh">` 跳转页，得先跟着跳过去。

---

## 关于配置文件（重要）

两个分支都用**独立的一份个人配置文件**装学号和密码：

| 分支 | 文件 | 模板 |
| --- | --- | --- |
| `python` | `config.toml` | `config.example.toml` |
| `powershell` | `config.ini` | `config.example.ini` |

这两个个人配置文件**已经被 `.gitignore` 忽略**，不会进仓库，所以可以放心写真实密码。
提交代码前建议顺手 `git status` 确认一下它没被带上。

---

## 目录 / 分支结构

```text
main 分支（本页）
├── README.md    # 你正在看的这份总说明
└── LICENSE      # MIT

python 分支
├── config.example.toml
├── config.py            # 读 config.toml 的加载器
├── login_once.py        # 登录一次
├── always_online.py     # 常驻，掉线重连
├── logger.py
├── autoConnectNetwork.bat
└── BitSrunLogin/        # 深澜认证协议实现（加密 + 登录流程）

powershell 分支
├── config.example.ini
├── uestc-login.ps1      # 核心：读配置 + 加密 + 登录 + 守护循环
├── autoConnectNetwork.bat
├── install-task.ps1     # 注册计划任务（推荐）
├── install-service.ps1  # 注册 Windows 服务（需 nssm/WinSW）
└── uninstall.ps1
```

---

## 许可

[MIT](LICENSE)。

本项目的登录流程实现衍生自 [coffeehat/BIT-srun-login-script](https://github.com/coffeehat/BIT-srun-login-script)，
因此 `LICENSE` 里**保留了上游作者的版权声明**（`Copyright (c) 2020 coffeehat`），
这是 MIT 协议的要求，请不要删掉。后面那行是我自己改动部分的声明。

---

## 参考与致谢

- [coffeehat/BIT-srun-login-script](https://github.com/coffeehat/BIT-srun-login-script)
  —— 最初的登录流程就是从这儿抄的。楼主入学的时候深澜的认证页面已经经过混淆了，
  全靠这个仓库才把流程理清楚。它里面还有支持 OpenWrt 的 go 版本。
- 好多学校都是这套登录逻辑，所以 GitHub 上同类脚本很多，遇到问题可以多搜几个对照着看。

---

## 免责声明

仅供个人学习和自用。请只在自己的账号上使用，不要拿去批量登录别人的账号或者做任何
未经授权的事。账号密码只保存在本地那份被 gitignore 的配置文件里，不会上传到任何地方；
但如果你自己不小心把它提交上去了，那是你的责任 —— 提交前记得 `git status` 看一眼。
