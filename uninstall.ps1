<#
.SYNOPSIS
    卸载 UESTC 校园网自动登录的计划任务 / Windows 服务。

.DESCRIPTION
    先尝试注销计划任务，再尝试移除服务；两者都不存在时不会报错。
    需要管理员权限（移除服务必须）。

.PARAMETER Name
    计划任务名 / 服务名，默认 UESTC-AutoLogin（和安装脚本保持一致）。

.EXAMPLE
    .\uninstall.ps1
#>
[CmdletBinding()]
param(
    [string]$Name = 'UESTC-AutoLogin'
)

$ErrorActionPreference = 'Stop'

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
           ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

$removed = $false

# --- 计划任务 -------------------------------------------------------------

$task = Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue
if ($task) {
    if (-not $isAdmin) { throw '移除计划任务需要管理员权限。' }
    Stop-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $Name -Confirm:$false
    Write-Host "已移除计划任务: $Name" -ForegroundColor Green
    $removed = $true
}

# --- Windows 服务 ---------------------------------------------------------

$svc = Get-Service -Name $Name -ErrorAction SilentlyContinue
if ($svc) {
    if (-not $isAdmin) { throw '移除服务需要管理员权限。' }

    $nssm = $null
    $local = Join-Path $PSScriptRoot 'nssm.exe'
    if (Test-Path -LiteralPath $local) { $nssm = $local }
    else {
        $cmd = Get-Command nssm.exe -ErrorAction SilentlyContinue
        if ($cmd) { $nssm = $cmd.Source }
    }

    if ($nssm) {
        & $nssm stop $Name confirm | Out-Null
        & $nssm remove $Name confirm
    }
    else {
        # 没有 nssm 就只能用 sc.exe 兜底（用 nssm 注册的服务同样能被 sc 删除）
        & sc.exe stop $Name | Out-Null
        & sc.exe delete $Name | Out-Null
    }

    Write-Host "已移除服务: $Name" -ForegroundColor Green
    $removed = $true
}

# --- 兜底：清理残留的守护进程 ---------------------------------------------
# Stop-ScheduledTask / nssm stop 有时杀不掉子进程，会留下一个还在跑的 -Daemon 实例。
# 按命令行精确匹配（脚本名 + -Daemon）来收尾，避免误伤其它 PowerShell 进程。
# 注意排除 $PID：如果本脚本自己被一段命令行里含 "uestc-login.ps1 ... -Daemon" 的
# 包装命令调用（例如从命令行里贴一段诊断脚本），那两个通配符会匹配到自己，导致自杀。
$lingering = @(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" -ErrorAction SilentlyContinue |
    Where-Object {
        $_.ProcessId -ne $PID -and
        $_.CommandLine -like '*uestc-login.ps1*' -and
        $_.CommandLine -like '*-Daemon*'
    })

foreach ($proc in $lingering) {
    Write-Host "清理残留守护进程 pid=$($proc.ProcessId)" -ForegroundColor Yellow
    Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
    $removed = $true
}

if (-not $removed) {
    Write-Host "没有找到名为 $Name 的计划任务或服务，无需清理。" -ForegroundColor DarkGray
}
