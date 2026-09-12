#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
UESTC 校园网自动登录 —— 管理与自启注册。

always_online.py 是**前台进程**，关掉终端窗口就跟着结束，只能用来测试。
本脚本负责把它注册成开机自启的后台进程，提供两种方式：

    计划任务（推荐）  零依赖，Windows 自带，随开机启动、以 SYSTEM 身份运行，
                      崩溃后自动重启。注销登录也能运行。
    Windows 服务     需要第三方包装器 nssm 或 WinSW。PowerShell / Python 脚本
                      无法直接 sc create（必须自行实现 SCM 的 ServiceMain
                      协议），所以必须借助包装器。

用法：

    python manage.py                 交互式菜单
    python manage.py install         注册计划任务（推荐）
    python manage.py uninstall       注销计划任务
    python manage.py start / stop    启动 / 停止计划任务
    python manage.py install-service 注册 Windows 服务（需 nssm）
    python manage.py uninstall-service
    python manage.py status          查看当前状态
    python manage.py selftest        加密实现自检
    python manage.py once            登录一次（等价于 login_once.py）
    python manage.py run             前台常驻（等价于 always_online.py）

注册计划任务和 Windows 服务都需要管理员权限。
"""
import ctypes
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DAEMON_SCRIPT = ROOT / 'always_online.py'
TASK_NAME = 'UESTC-AutoLogin'
SERVICE_NAME = 'UESTC-AutoLogin'

# 服务包装器的下载地址，仅在用户选择服务方式且本机没有时打印
NSSM_URL = 'https://nssm.cc/download'
WINSW_URL = 'https://github.com/winsw/winsw/releases'


# --------------------------------------------------------------------------
# 通用工具
# --------------------------------------------------------------------------

def is_admin():
    """当前进程是否具有管理员权限。"""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def require_admin(action):
    """注册 / 注销类操作需要管理员权限，否则直接给出提示而不是报一堆错。"""
    if is_admin():
        return True
    print(f'\n[!] {action}需要管理员权限。')
    print('    请右键点击 命令提示符 / Windows Terminal，选择「以管理员身份运行」，')
    print('    然后在打开的窗口里重新执行本命令。')
    return False


def _configure_stdout():
    """
    让打印不因编码问题崩溃。

    本程序要回显 schtasks / sc 等系统命令的输出，而那些文本的编码取决于控制台
    的 OEM 代码页（中文系统上是 GBK），本文件自身却是 UTF-8。两者对不上时
    Python 会抛 UnicodeEncodeError 而不是把那一行打出来。把错误处理改成
    replace，无法编码的字符退化成 '?'，不影响其余输出。

    实测（2026-09-13）：没有这一段时，`manage.py status` 在输出被重定向到管道
    或文件时会因 schtasks 的一行本地化文本直接崩溃。
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors='replace')
        except (AttributeError, ValueError):
            pass


def _decode_console(raw):
    """
    按控制台的 OEM 代码页解码系统命令的输出。

    schtasks / sc / net 这类命令的输出跟随 OEM 代码页（中文系统为 GBK）而不是
    UTF-8，用 utf-8 解会得到一串替换字符。先试 OEM，再退回 UTF-8。
    """
    for enc in ('oem', 'utf-8', 'gbk'):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode('utf-8', errors='replace')


def run(cmd, quiet=False, **kwargs):
    """
    执行一条命令并回显。返回 (returncode, 输出文本)。

    不抛异常：调用方通常只关心退出码（例如 schtasks /Query 用退出码表示任务
    是否存在），交给调用方判断更清楚。

    quiet=True 用于「查询」类调用：目标不存在时这些命令会打印一段本地化的
    报错，回显出来只会干扰正常输出，而调用方本来就用退出码判断。
    """
    if not quiet:
        print(f'  > {" ".join(str(c) for c in cmd)}')
    # 不用 text=True：需要先拿到原始字节，再按 OEM 代码页解码
    proc = subprocess.run(cmd, capture_output=True, **kwargs)
    out = _decode_console((proc.stdout or b'') + (proc.stderr or b''))
    if out.strip() and not quiet:
        for line in out.strip().splitlines():
            print(f'    {line}')
    return proc.returncode, out


def python_exe():
    """
    注册自启时要写进任务/服务的解释器绝对路径。

    必须用绝对路径：计划任务以 SYSTEM 身份运行，那里没有用户 PATH，conda 之类
    的环境更是完全不生效。sys.executable 就是当前正在运行本脚本的解释器。
    """
    exe = sys.executable
    if not exe or not Path(exe).exists():
        print('[!] 无法确定 python 解释器的绝对路径，请用绝对路径显式运行本脚本。')
        sys.exit(1)
    return exe


def check_config():
    """注册自启前先确认 config.toml 存在，否则任务会在开机后一直失败。"""
    cfg = ROOT / 'config.toml'
    if cfg.exists():
        return True
    print(f'\n[!] 找不到配置文件 {cfg}')
    print('    请先复制模板并填写账号：')
    print('        copy config.example.toml config.toml')
    print('    否则注册好的任务每次启动都会立即失败。')
    return False


def remember_python(py):
    """
    把当前解释器的路径记到 python-path.txt，供 autoConnectNetwork.bat 使用。

    bat 本身无法可靠地找到 Python：PATH 上的 "python" 常常是微软商店的占位
    程序，而 conda 只把安装目录下的 Scripts 加进 PATH，python.exe 并不在里面。
    注册自启时既然已经确定了一个能用的解释器，就顺手记下来，之后双击 bat 不必
    再猜，也不怕用户之后改 PATH。

    文件用 '\\n' 换行：bat 里用 `set /p` 读取，CRLF 会在行尾留下一个 \\r。
    """
    path = ROOT / 'python-path.txt'
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(str(py) + '\n')
    return path


# --------------------------------------------------------------------------
# 计划任务
# --------------------------------------------------------------------------

def task_xml(py, script):
    """
    生成计划任务的 XML。

    必须用 XML 而不是 schtasks 的普通参数：命令行参数无法表达以下四点，而这
    四点对「长期常驻」都是必需的。

      ExecutionTimeLimit=PT0S    不限制运行时长。不加的话默认 72 小时，
                                 到点任务会被强制结束 —— 守护进程正好是最怕
                                 这个的。
      RestartOnFailure           进程异常退出后自动重启。
      MultipleInstancesPolicy    已在运行时不再启动第二个实例，避免两个进程
                                 同时反复登录。
      Battery 相关设置           笔记本用电池时也照常运行、不因切换到电池而停止。

    触发器用开机启动（BootTrigger）而不是登录时启动：认证是按机器 IP 进行的，
    与桌面会话无关，因此注销后也应当继续运行。
    """
    script = str(script)
    return f'''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>UESTC 校园网自动登录：开机后常驻运行，检测到断网自动重新认证。</Description>
    <URI>\\{TASK_NAME}</URI>
  </RegistrationInfo>
  <Triggers>
    <BootTrigger>
      <!-- 开机后等 30 秒再启动，避开系统刚起来时网络栈尚未就绪的阶段 -->
      <Enabled>true</Enabled>
      <Delay>PT30S</Delay>
    </BootTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <!-- S-1-5-18 = SYSTEM，无需存储账号密码，注销后仍可运行 -->
      <UserId>S-1-5-18</UserId>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <!-- PT0S = 不限制运行时长，见函数注释 -->
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
    <RestartOnFailure>
      <Interval>PT1M</Interval>
      <Count>999</Count>
    </RestartOnFailure>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{py}</Command>
      <Arguments>"{script}"</Arguments>
      <WorkingDirectory>{ROOT}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
'''


def task_exists():
    rc, _ = run(['schtasks', '/Query', '/TN', TASK_NAME], quiet=True)
    return rc == 0


def install_task():
    if not require_admin('注册计划任务'):
        return 1
    if not check_config():
        return 1

    py = python_exe()
    remember_python(py)
    xml = task_xml(py, DAEMON_SCRIPT)

    # 任务计划程序要求 XML 为 UTF-16 编码，用 utf-16 写出会带上 BOM。
    # 临时文件放在系统临时目录，注册完即删除。
    fd, tmp = tempfile.mkstemp(suffix='.xml', prefix='uestc-task-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-16') as f:
            f.write(xml)
        rc, _ = run(['schtasks', '/Create', '/TN', TASK_NAME, '/XML', tmp, '/F'])
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass

    if rc != 0:
        print('\n[!] 计划任务注册失败。')
        return rc

    print(f'''
[+] 计划任务「{TASK_NAME}」已注册。

    解释器  {py}
    脚本    {DAEMON_SCRIPT}
    触发    开机后 30 秒
    身份    SYSTEM（注销后仍运行）
    保活    异常退出 1 分钟后自动重启，不限运行时长

    立即启动：python manage.py start
    查看状态：python manage.py status
    查看日志：{ROOT / 'logs'}
''')
    return 0


def uninstall_task():
    if not require_admin('注销计划任务'):
        return 1
    if not task_exists():
        print(f'[i] 计划任务「{TASK_NAME}」本来就不存在，无需注销。')
        return 0

    run(['schtasks', '/End', '/TN', TASK_NAME])       # 先停掉在跑的实例
    rc, _ = run(['schtasks', '/Delete', '/TN', TASK_NAME, '/F'])
    print(f'[+] 计划任务「{TASK_NAME}」已注销。' if rc == 0 else '\n[!] 注销失败。')
    return rc


def start_task():
    if not require_admin('启动计划任务'):
        return 1
    if not task_exists():
        print(f'[i] 计划任务「{TASK_NAME}」尚未注册，先执行：python manage.py install')
        return 1
    rc, _ = run(['schtasks', '/Run', '/TN', TASK_NAME])
    print('[+] 已请求启动。' if rc == 0 else '\n[!] 启动失败。')
    return rc


def stop_task():
    if not require_admin('停止计划任务'):
        return 1
    if not task_exists():
        print(f'[i] 计划任务「{TASK_NAME}」尚未注册。')
        return 1
    rc, _ = run(['schtasks', '/End', '/TN', TASK_NAME])
    print('[+] 已请求停止。' if rc == 0 else '\n[!] 停止失败。')
    return rc


# --------------------------------------------------------------------------
# Windows 服务（需要 nssm / WinSW 包装）
# --------------------------------------------------------------------------

def find_wrapper():
    """
    找到可用的服务包装器。

    Python / PowerShell 脚本无法直接注册成服务：Windows 服务必须实现 SCM 的
    ServiceMain 回调并按协议上报状态，解释型脚本做不到，所以需要一个包装器把
    普通进程托管成服务。这里只查找、不自动下载第三方二进制。
    """
    for name in ('nssm.exe', 'nssm'):
        path = shutil.which(name)
        if path:
            return 'nssm', path
    local = ROOT / 'nssm.exe'
    if local.exists():
        return 'nssm', str(local)

    for name in ('WinSW.exe', 'winsw.exe'):
        path = shutil.which(name)
        if path:
            return 'winsw', path
    return None, None


def service_exists():
    rc, _ = run(['sc', 'query', SERVICE_NAME], quiet=True)
    return rc == 0


def install_service():
    if not require_admin('注册 Windows 服务'):
        return 1
    if not check_config():
        return 1

    kind, wrapper = find_wrapper()
    if not kind:
        print(f'''
[!] 本机没有找到服务包装器 nssm 或 WinSW。

    Python 脚本不能直接注册成 Windows 服务（服务必须实现 SCM 的 ServiceMain
    协议，脚本语言做不到），因此需要一个包装器把 python 进程托管成服务。

    两种选择：

    1) 直接用计划任务 —— 零依赖，功能上完全够用，也是本项目的推荐方式：
           python manage.py install

    2) 下载 nssm（约 300 KB，单文件）后重新执行本命令：
           {NSSM_URL}
       把 nssm.exe 放进 PATH，或直接放在本项目目录下。

    本项目不自动下载第三方二进制，需要你自己确认来源后再放入。
''')
        return 1

    py = python_exe()
    remember_python(py)

    if kind == 'nssm':
        run([wrapper, 'install', SERVICE_NAME, py, str(DAEMON_SCRIPT)])
        run([wrapper, 'set', SERVICE_NAME, 'AppDirectory', str(ROOT)])
        run([wrapper, 'set', SERVICE_NAME, 'DisplayName', 'UESTC 校园网自动登录'])
        run([wrapper, 'set', SERVICE_NAME, 'Description',
             '检测到断网时自动重新认证校园网'])
        # 进程退出后自动重启，间隔 60 秒
        run([wrapper, 'set', SERVICE_NAME, 'AppExit', 'Default', 'Restart'])
        run([wrapper, 'set', SERVICE_NAME, 'AppRestartDelay', '60000'])
        run([wrapper, 'set', SERVICE_NAME, 'Start', 'SERVICE_AUTO_START'])
        rc, _ = run([wrapper, 'start', SERVICE_NAME])
        if rc != 0 and service_exists():
            # 服务已注册但启动失败（例如刚好已经启动），注册本身是成功的
            rc = 0
    else:
        # WinSW 用同目录同名的 xml 作为配置
        xml_path = ROOT / f'{SERVICE_NAME}.xml'
        xml_path.write_text(f'''<service>
  <id>{SERVICE_NAME}</id>
  <name>UESTC 校园网自动登录</name>
  <description>检测到断网时自动重新认证校园网</description>
  <executable>{py}</executable>
  <arguments>"{DAEMON_SCRIPT}"</arguments>
  <workingdirectory>{ROOT}</workingdirectory>
  <startmode>Automatic</startmode>
  <onfailure action="restart" delay="60 sec" />
  <logmode>none</logmode>
</service>
''', encoding='utf-8')
        print(f'[i] 已生成 WinSW 配置：{xml_path}')
        rc, _ = run([wrapper, 'install', str(xml_path)])
        if rc == 0:
            run([wrapper, 'start', str(xml_path)])

    if rc == 0:
        print(f'''
[+] Windows 服务「{SERVICE_NAME}」已注册并启动（包装器：{wrapper}）。
    查看状态：python manage.py status
    卸载服务：python manage.py uninstall-service
''')
    else:
        print('\n[!] 服务注册失败，请检查上面的输出。')
    return rc


def uninstall_service():
    if not require_admin('注销 Windows 服务'):
        return 1
    if not service_exists():
        print(f'[i] Windows 服务「{SERVICE_NAME}」本来就不存在，无需注销。')
        return 0

    kind, wrapper = find_wrapper()
    if kind == 'nssm':
        run([wrapper, 'stop', SERVICE_NAME])
        rc, _ = run([wrapper, 'remove', SERVICE_NAME, 'confirm'])
    elif kind == 'winsw':
        xml_path = ROOT / f'{SERVICE_NAME}.xml'
        run([wrapper, 'stop', str(xml_path)])
        rc, _ = run([wrapper, 'uninstall', str(xml_path)])
    else:
        # 包装器被删了，退回用 sc 直接删（服务已停止时可用）
        run(['sc', 'stop', SERVICE_NAME])
        rc, _ = run(['sc', 'delete', SERVICE_NAME])

    print(f'[+] Windows 服务「{SERVICE_NAME}」已注销。' if rc == 0 else '\n[!] 注销失败。')
    return rc


# --------------------------------------------------------------------------
# 状态
# --------------------------------------------------------------------------

def query_task_xml():
    """
    导出已注册任务的 XML 文本；未注册或解析失败时返回 None。

    不用 `schtasks /FO LIST /V` 的文本输出来读设置：那是本地化的，而且会刷出
    三四十行。XML 的标签名与系统语言无关，且能精确看到保活相关的设置。
    """
    proc = subprocess.run(['schtasks', '/Query', '/TN', TASK_NAME, '/XML'],
                          capture_output=True)
    raw = proc.stdout or b''
    if proc.returncode != 0 or not raw:
        return None
    # 导出的是 UTF-16(带 BOM)，不是控制台的 OEM 代码页
    if raw[:2] in (b'\xff\xfe', b'\xfe\xff'):
        return raw.decode('utf-16', errors='replace')
    return _decode_console(raw)


def _tag(text, name):
    """取 <name>...</name> 的内容（去空白）；没有则返回 None。"""
    m = re.search(rf'<{name}>(.*?)</{name}>', text, re.S)
    return ' '.join(m.group(1).split()) if m else None


def daemon_pids():
    """
    找出正在运行的守护进程 pid。

    按进程名加命令行关键字匹配，而不是查任务计划程序的「状态」字段 —— 后者的
    取值是本地化文本，换个系统语言就匹配不上了。
    """
    ps = ('Get-CimInstance Win32_Process -Filter "Name=\'python.exe\'" | '
          'Where-Object { $_.CommandLine -like \'*always_online.py*\' } | '
          'ForEach-Object { $_.ProcessId }')
    proc = subprocess.run(['powershell', '-NoProfile', '-Command', ps],
                          capture_output=True)
    out = _decode_console(proc.stdout or b'')
    return [line.strip() for line in out.splitlines() if line.strip().isdigit()]


def status():
    print(f'\n项目目录  {ROOT}')
    print(f'解释器    {sys.executable}')

    cfg = ROOT / 'config.toml'
    # 不要在这里用对勾、叉号之类的符号(U+2713 / U+2717)：它们不在 GBK 字符集里，
    # 一旦把输出重定向到文件或管道，Python 会退回 GBK 编码并直接抛
    # UnicodeEncodeError。中文本身在 GBK 内有对应码位，可以放心用。
    print(f'配置文件  {cfg}  {"已存在" if cfg.exists() else "缺失（见 config.example.toml）"}')

    pids = daemon_pids()
    print(f'守护进程  ' + (f'运行中，pid {" ".join(pids)}' if pids
                           else '未在运行'))

    print(f'\n--- 计划任务「{TASK_NAME}」---')
    if not task_exists():
        print('    未注册（python manage.py install 可注册）')
    else:
        xml = query_task_xml() or ''
        print('    已注册')
        cmd, args = _tag(xml, 'Command'), _tag(xml, 'Arguments')
        if cmd:
            print(f'    启动命令  {cmd} {args or ""}')
        user = _tag(xml, 'UserId')
        print(f'    运行身份  {user or "?"}'
              + ('（SYSTEM，注销后仍运行）' if user == 'S-1-5-18' else ''))
        limit = _tag(xml, 'ExecutionTimeLimit')
        print(f'    运行时长  ' + ('不限制' if limit == 'PT0S' else str(limit)))
        count, interval = _tag(xml, 'Count'), _tag(xml, 'Interval')
        print(f'    失败重启  ' + (f'{interval} 后重试，最多 {count} 次'
                                   if count else '未设置'))
        if 'BootTrigger' in xml:
            print(f'    触发器    开机后 {_tag(xml, "Delay") or "立即"}')

    print(f'\n--- Windows 服务「{SERVICE_NAME}」---')
    if not service_exists():
        print('    未注册（python manage.py install-service 可注册，需 nssm）')
    else:
        rc, out = run(['sc', 'query', SERVICE_NAME], quiet=True)
        for line in out.splitlines():
            if line.strip():
                print(f'    {line.strip()}')

    print(f'\n--- 说明 ---')
    print('    always_online.py 在前台运行时，关掉终端窗口就会结束；')
    print('    注册成计划任务或服务后才会开机自启、长期驻留。')
    print(f'\n日志目录  {ROOT / "logs"}\n')
    return 0


# --------------------------------------------------------------------------
# 前台运行
# --------------------------------------------------------------------------

def run_once():
    """登录一次，等价于 python login_once.py。"""
    return subprocess.call([sys.executable, str(ROOT / 'login_once.py')])


def run_daemon():
    """前台常驻，等价于 python always_online.py。"""
    print('[i] 前台运行中，按 Ctrl+C 退出。')
    print('[i] 这样运行的进程会随终端关闭而结束，长期无人值守请用 python manage.py install\n')
    try:
        return subprocess.call([sys.executable, str(DAEMON_SCRIPT)])
    except KeyboardInterrupt:
        print('\n[i] 已退出。')
        return 0


def run_selftest():
    return subprocess.call([sys.executable, str(ROOT / 'selftest.py')])


# --------------------------------------------------------------------------
# 交互式菜单
# --------------------------------------------------------------------------

MENU = [
    ('once',              '登录一次（验证配置是否正确）'),
    ('run',               '前台常驻运行（仅用于测试，关掉终端就停）'),
    ('install',           '注册开机自启 —— 计划任务（推荐，零依赖）'),
    ('uninstall',         '注销计划任务'),
    ('start',             '启动计划任务'),
    ('stop',              '停止计划任务'),
    ('install-service',   '注册 Windows 服务（需 nssm/WinSW）'),
    ('uninstall-service', '注销 Windows 服务'),
    ('status',            '查看当前状态'),
    ('selftest',          '加密实现自检'),
]

ACTIONS = {
    'once': run_once,
    'run': run_daemon,
    'install': install_task,
    'uninstall': uninstall_task,
    'start': start_task,
    'stop': stop_task,
    'install-service': install_service,
    'uninstall-service': uninstall_service,
    'status': status,
    'selftest': run_selftest,
}


def menu():
    print('\n' + '=' * 56)
    print('  UESTC 校园网自动登录')
    print('=' * 56)
    for i, (_, desc) in enumerate(MENU, 1):
        print(f'  {i:2d}. {desc}')
    print('   0. 退出')
    print('=' * 56)
    if not is_admin():
        print('  提示：注册 / 注销自启需要管理员权限，当前不是管理员。')
        print('        双击 autoConnectNetwork.bat 时，请右键选择「以管理员身份运行」。')

    choice = input('\n请选择: ').strip()
    if choice in ('0', ''):
        return 0
    if not choice.isdigit() or not (1 <= int(choice) <= len(MENU)):
        print('[!] 无效的选择。')
        return 1

    cmd = MENU[int(choice) - 1][0]
    rc = ACTIONS[cmd]()
    if cmd not in ('run', 'once', 'selftest'):
        input('\n按回车键返回...')
    return rc or 0


def main(argv):
    if not argv:
        while True:
            rc = menu()
            if rc == 0:
                return 0

    cmd = argv[0]
    if cmd in ('-h', '--help', 'help'):
        print(__doc__)
        return 0
    if cmd not in ACTIONS:
        print(f'[!] 未知命令：{cmd}\n')
        print(__doc__)
        return 2
    return ACTIONS[cmd]() or 0


if __name__ == '__main__':
    _configure_stdout()
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        print('\n[i] 已中断。')
        sys.exit(130)
