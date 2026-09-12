<#
.SYNOPSIS
    把 UESTC 校园网自动登录注册成 Windows 服务（备选方案，需要 nssm 或 WinSW）。

.DESCRIPTION
    为什么不能直接用 sc.exe 注册？

    Windows 服务必须实现 SCM 的 ServiceMain / 状态上报协议，而 PowerShell 脚本不是
    服务宿主程序，所以 sc.exe create 指向 powershell.exe 是起不来的。标准做法是用一个
    服务包装器（nssm 或 WinSW）把 powershell.exe 包成一个真正的服务。

    本脚本只检测本机有没有包装器，不会自动下载第三方二进制。

    如果你只是想在开机时自动登录、掉线重连，推荐直接用 install-task.ps1（零依赖）。

.PARAMETER ServiceName
    服务名，默认 UESTC-AutoLogin。

.PARAMETER NssmPath
    nssm.exe 的路径。不指定则在 PATH 和脚本目录里找。
#>
[CmdletBinding()]
param(
    [string]$ServiceName = 'UESTC-AutoLogin',
    [string]$NssmPath
)

$ErrorActionPreference = 'Stop'

$scriptPath = Join-Path $PSScriptRoot 'uestc-login.ps1'
if (-not (Test-Path -LiteralPath $scriptPath)) { throw "找不到 $scriptPath" }

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
           ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    throw '注册服务需要管理员权限。请用「以管理员身份运行」打开 PowerShell 再执行。'
}

# --- 找包装器 -------------------------------------------------------------

function Find-Nssm {
    param([string]$Explicit)
    if ($Explicit) {
        if (Test-Path -LiteralPath $Explicit) { return (Resolve-Path -LiteralPath $Explicit).Path }
        throw "指定的 nssm 不存在: $Explicit"
    }
    $local = Join-Path $PSScriptRoot 'nssm.exe'
    if (Test-Path -LiteralPath $local) { return $local }
    $cmd = Get-Command nssm.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}

$nssm = Find-Nssm -Explicit $NssmPath

if (-not $nssm) {
    Write-Host '没有找到 nssm.exe 或 WinSW.exe。' -ForegroundColor Yellow
    Write-Host ''
    Write-Host 'Windows 服务必须靠一个包装器才能托管 PowerShell 脚本。请任选其一：'
    Write-Host ''
    Write-Host '  方案 A —— nssm（推荐，最简单）' -ForegroundColor Cyan
    Write-Host '    1. 从 https://nssm.cc/download 下载，解压出 win64\nssm.exe'
    Write-Host "    2. 把 nssm.exe 放到 $PSScriptRoot"
    Write-Host '    3. 重新运行本脚本'
    Write-Host ''
    Write-Host '  方案 B —— WinSW' -ForegroundColor Cyan
    Write-Host '    1. 从 https://github.com/winsw/winsw/releases 下载 WinSW-x64.exe'
    Write-Host "    2. 重命名为 $ServiceName.exe 并放到 $PSScriptRoot"
    Write-Host '    3. 重新运行本脚本'
    Write-Host ''
    Write-Host '如果你只是想开机自动登录，直接用 install-task.ps1 就行，不需要任何第三方文件。' -ForegroundColor Green
    exit 1
}

# --- nssm 注册 -------------------------------------------------------------

$logDir = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path -LiteralPath $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }

$svcArgs = '-NoProfile -ExecutionPolicy Bypass -File "{0}" -Daemon' -f $scriptPath

Write-Host "使用 nssm: $nssm"
& $nssm install $ServiceName 'powershell.exe' $svcArgs
if ($LASTEXITCODE -ne 0) { throw "nssm install 失败 (exit $LASTEXITCODE)" }

& $nssm set $ServiceName AppExit Default Restart      | Out-Null   # 挂了自动重启
& $nssm set $ServiceName AppStdout (Join-Path $logDir 'service.out.log') | Out-Null
& $nssm set $ServiceName AppStderr (Join-Path $logDir 'service.err.log') | Out-Null
& $nssm set $ServiceName Start SERVICE_AUTO_START      | Out-Null

Write-Host "已注册服务: $ServiceName" -ForegroundColor Green
& $nssm start $ServiceName
Write-Host ''
& $nssm status $ServiceName
Write-Host ''
Write-Host '卸载: .\uninstall.ps1' -ForegroundColor DarkGray
