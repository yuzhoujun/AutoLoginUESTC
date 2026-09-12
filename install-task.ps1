<#
.SYNOPSIS
    把 UESTC 校园网自动登录注册成计划任务（开机自启 + 掉线自动重连）。

.DESCRIPTION
    以 SYSTEM 身份在开机时运行 uestc-login.ps1 -Daemon。
    因为认证是按机器 IP 做的，不依赖桌面会话，所以不需要保持用户登录，
    也不需要把密码存进任务计划程序。

    需要管理员权限。

.PARAMETER TaskName
    计划任务名称，默认 UESTC-AutoLogin。

.PARAMETER NoStart
    只注册不立即启动。

.EXAMPLE
    .\install-task.ps1
    .\install-task.ps1 -TaskName MyLogin -NoStart
#>
[CmdletBinding()]
param(
    [string]$TaskName = 'UESTC-AutoLogin',
    [switch]$NoStart
)

$ErrorActionPreference = 'Stop'

$scriptPath = Join-Path $PSScriptRoot 'uestc-login.ps1'
if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "找不到 $scriptPath"
}

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
           ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    throw '注册计划任务需要管理员权限。请用「以管理员身份运行」打开 PowerShell 再执行。'
}

$action = New-ScheduledTaskAction -Execute 'powershell.exe' `
    -Argument ('-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "{0}" -Daemon' -f $scriptPath)

# 开机触发，延迟 30 秒等网络栈就绪（守护循环本来也会重试，这里只是少几次无用功）
$trigger = New-ScheduledTaskTrigger -AtStartup
$trigger.Delay = 'PT30S'

$principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero)      # 不限运行时长

Register-ScheduledTask -TaskName $TaskName `
    -Action $action -Trigger $trigger -Principal $principal -Settings $settings `
    -Description 'UESTC 校园网自动登录，掉线自动重连（纯 PowerShell 实现）' -Force | Out-Null

Write-Host "已注册计划任务: $TaskName" -ForegroundColor Green
Write-Host "  脚本:   $scriptPath"
Write-Host "  身份:   SYSTEM (开机自启，不需要用户登录)"
Write-Host "  日志:   $(Join-Path $PSScriptRoot 'logs\uestc-login.log')"

if (-not $NoStart) {
    Start-ScheduledTask -TaskName $TaskName
    Start-Sleep -Seconds 2
    $info = Get-ScheduledTask -TaskName $TaskName | Get-ScheduledTaskInfo
    Write-Host "  状态:   $((Get-ScheduledTask -TaskName $TaskName).State)"
    Write-Host "  上次结果: $($info.LastTaskResult)"
}

Write-Host ''
Write-Host '卸载: .\uninstall.ps1' -ForegroundColor DarkGray
