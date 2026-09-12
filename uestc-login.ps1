<#
.SYNOPSIS
    UESTC 电子科技大学校园网认证 —— 纯 PowerShell 实现（不依赖 Python）

.DESCRIPTION
    深澜(srun)认证协议的完整实现：取 IP -> 取 token -> XXTEA 加密 -> HMAC-MD5 -> SHA1 校验和 -> 登录。
    加密部分逐字节对齐 BitSrunLogin/encryption/ 里的 Python 参考实现，可用 -SelfTest 自检。

.PARAMETER Once
    登录一次就退出（默认）。用于验证配置是否正确。

.PARAMETER Daemon
    常驻运行，定时探测网络，掉线自动重连。

.PARAMETER SelfTest
    用黄金向量自检加密函数，不联网。

.PARAMETER ConfigPath
    配置文件路径，默认同目录下的 config.ini。

.EXAMPLE
    .\uestc-login.ps1 -Once
    .\uestc-login.ps1 -Daemon
    .\uestc-login.ps1 -SelfTest
#>
[CmdletBinding()]
param(
    [switch]$Once,
    [switch]$Daemon,
    [switch]$SelfTest,
    [string]$ConfigPath
)

$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

$script:UserAgent = 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.26 Safari/537.36'

# 深澜自定义 base64 字母表（不是标准 base64）
$script:SrunAlpha = 'LVoJPiCN2R8G90yg+hmFHuacZ1OWMnrsSTXkYpUq/3dlbfKwv6xztjI7DeBE45QA'

# 32 位掩码。必须写成 0xFFFFFFFFL —— PS 5.1 里 0xFFFFFFFF 和 [int64]0xFFFFFFFF 都会被解析成
# Int32/Int64 的 -1，起不到任何掩码作用，会导致 XXTEA 的中间结果溢出成浮点数。
$script:MASK32 = 0xFFFFFFFFL

# 协议固定参数
$script:SrunN     = '200'
$script:SrunVType = '1'
$script:SrunEnc   = 'srun_bx1'

# 黄金向量：从 Python 参考实现采集，用于 -SelfTest
$script:TestKey = 'abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789'
$script:TestMsg = '{"username":"1234567890@dx","password":"pw","ip":"10.0.0.1","acid":"3","enc_ver":"srun_bx1"}'

# ---------------------------------------------------------------------------
# 加密 —— 移植自 BitSrunLogin/encryption/
# ---------------------------------------------------------------------------

function Get-SrunBase64 {
    <#  对应 srun_base64.get_base64：用自定义字母表的 base64  #>
    param([byte[]]$Bytes)

    if ($null -eq $Bytes -or $Bytes.Length -eq 0) { return '' }

    $alpha = $script:SrunAlpha
    $sb    = New-Object System.Text.StringBuilder
    $imax  = $Bytes.Length - ($Bytes.Length % 3)

    for ($i = 0; $i -lt $imax; $i += 3) {
        $b10 = ([int]$Bytes[$i] -shl 16) -bor ([int]$Bytes[$i + 1] -shl 8) -bor [int]$Bytes[$i + 2]
        [void]$sb.Append($alpha[($b10 -shr 18) -band 63])
        [void]$sb.Append($alpha[($b10 -shr 12) -band 63])
        [void]$sb.Append($alpha[($b10 -shr 6)  -band 63])
        [void]$sb.Append($alpha[$b10 -band 63])
    }

    $rem = $Bytes.Length - $imax
    if ($rem -eq 1) {
        $b10 = [int]$Bytes[$imax] -shl 16
        [void]$sb.Append($alpha[($b10 -shr 18) -band 63])
        [void]$sb.Append($alpha[($b10 -shr 12) -band 63])
        [void]$sb.Append('==')
    }
    elseif ($rem -eq 2) {
        $b10 = ([int]$Bytes[$imax] -shl 16) -bor ([int]$Bytes[$imax + 1] -shl 8)
        [void]$sb.Append($alpha[($b10 -shr 18) -band 63])
        [void]$sb.Append($alpha[($b10 -shr 12) -band 63])
        [void]$sb.Append($alpha[($b10 -shr 6) -band 63])
        [void]$sb.Append('=')
    }

    return $sb.ToString()
}

function ConvertTo-SrunWords {
    <#  对应 srun_xencode.sencode：4 字节小端打包成 32 位字，可选追加原始长度  #>
    param(
        [byte[]]$Bytes,
        [bool]$AppendLength
    )

    $words = New-Object 'System.Collections.Generic.List[int64]'
    $l     = $Bytes.Length

    for ($i = 0; $i -lt $l; $i += 4) {
        $w = [int64]0
        if (($i + 1) -le $l) { $w = $w -bor ([int64]$Bytes[$i] -shl 0) }
        if (($i + 2) -le $l) { $w = $w -bor ([int64]$Bytes[$i + 1] -shl 8) }
        if (($i + 3) -le $l) { $w = $w -bor ([int64]$Bytes[$i + 2] -shl 16) }
        if (($i + 4) -le $l) { $w = $w -bor ([int64]$Bytes[$i + 3] -shl 24) }
        $words.Add($w -band $script:MASK32)
    }

    if ($AppendLength) { $words.Add([int64]$l) }
    return $words
}

function Get-XEncode {
    <#
      对应 srun_xencode.get_xencode：XXTEA 变体，返回字节数组。

      PS 5.1 关键点：全程用 [int64] 并在每步用 -band $script:MASK32 收敛回 32 位无符号范围。
      PowerShell 默认 Int32 会溢出，且 -shr 对负数做算术右移会补符号位，都会导致结果错误。
    #>
    param(
        [string]$Message,
        [string]$Key
    )

    if ([string]::IsNullOrEmpty($Message)) { return [byte[]]@() }

    $pwd  = ConvertTo-SrunWords -Bytes ([Text.Encoding]::UTF8.GetBytes($Message)) -AppendLength $true
    $pwdk = ConvertTo-SrunWords -Bytes ([Text.Encoding]::UTF8.GetBytes($Key))     -AppendLength $false
    while ($pwdk.Count -lt 4) { $pwdk.Add([int64]0) }

    $n = $pwd.Count - 1
    $z = $pwd[$n]
    $y = $pwd[0]
    $c = [int64]0x9E3779B9          # = 0x86014019 | 0x183639A0
    $d = [int64]0
    $m = [int64]0
    $e = [int64]0
    $p = 0
    $q = [int][math]::Floor(6 + 52 / ($n + 1))

    while ($q -gt 0) {
        $d = ($d + $c) -band $script:MASK32
        $e = ($d -shr 2) -band 3
        $p = 0
        while ($p -lt $n) {
            $y = $pwd[$p + 1]
            $m = ($z -shr 5) -bxor ($y -shl 2)
            $m = $m + ((($y -shr 3) -bxor ($z -shl 4)) -bxor ($d -bxor $y))
            $m = $m + (($pwdk[($p -band 3) -bxor $e]) -bxor $z)
            $pwd[$p] = ($pwd[$p] + $m) -band $script:MASK32
            $z = $pwd[$p]
            $p = $p + 1
        }

        $y = $pwd[0]
        $m = ($z -shr 5) -bxor ($y -shl 2)
        $m = $m + ((($y -shr 3) -bxor ($z -shl 4)) -bxor ($d -bxor $y))
        $m = $m + (($pwdk[($p -band 3) -bxor $e]) -bxor $z)
        $pwd[$n] = ($pwd[$n] + $m) -band $script:MASK32
        $z = $pwd[$n]

        $q = $q - 1
    }

    # 对应 lencode(pwd, key=False)：每个字拆成 4 个小端字节
    $out = New-Object 'System.Collections.Generic.List[byte]'
    foreach ($w in $pwd) {
        $out.Add([byte]($w -band 0xFF))
        $out.Add([byte](($w -shr 8)  -band 0xFF))
        $out.Add([byte](($w -shr 16) -band 0xFF))
        $out.Add([byte](($w -shr 24) -band 0xFF))
    }
    return $out.ToArray()
}

function Get-HmacMd5 {
    <#  对应 srun_md5.get_md5：HMAC-MD5，key=token，message=password（不是普通 MD5！）  #>
    param(
        [string]$Key,
        [string]$Message
    )

    $h = New-Object System.Security.Cryptography.HMACMD5
    try {
        $h.Key  = [Text.Encoding]::UTF8.GetBytes($Key)
        $hash   = $h.ComputeHash([Text.Encoding]::UTF8.GetBytes($Message))
    }
    finally { $h.Dispose() }

    return (($hash | ForEach-Object { $_.ToString('x2') }) -join '')
}

function Get-Sha1 {
    <#  对应 srun_sha1.get_sha1  #>
    param([string]$Value)

    $sha = [System.Security.Cryptography.SHA1]::Create()
    try   { $hash = $sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($Value)) }
    finally { $sha.Dispose() }

    return (($hash | ForEach-Object { $_.ToString('x2') }) -join '')
}

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

function Read-UestcConfig {
    <#
      解析 config.ini。支持 [section] 和整行注释（; 或 #）。
      注意：不支持行尾注释 —— 因为密码里可能包含 ; 或 #，截断会静默导致登录失败。
    #>
    param([string]$Path)

    if ([string]::IsNullOrEmpty($Path)) {
        $Path = Join-Path $PSScriptRoot 'config.ini'
    }
    if (-not (Test-Path -LiteralPath $Path)) {
        throw ("找不到配置文件 {0}`n" +
               "请先把 config.example.ini 复制成 config.ini，并填上你的学号和密码。") -f $Path
    }

    $cfg     = @{}
    $section = ''

    foreach ($raw in (Get-Content -LiteralPath $Path -Encoding UTF8)) {
        $line = $raw.Trim()
        if ($line -eq '' -or $line.StartsWith(';') -or $line.StartsWith('#')) { continue }

        if ($line -match '^\[(.+)\]$') {
            $section = $Matches[1].Trim()
            if (-not $cfg.ContainsKey($section)) { $cfg[$section] = @{} }
            continue
        }

        $idx = $line.IndexOf('=')
        if ($idx -lt 1 -or $section -eq '') { continue }

        $key = $line.Substring(0, $idx).Trim()
        $val = $line.Substring($idx + 1).Trim()
        $cfg[$section][$key] = $val
    }

    foreach ($req in @(@('account', 'username'), @('account', 'password'), @('portal', 'url'), @('portal', 'ac_id'))) {
        $sec = $req[0]
        $key = $req[1]
        if (-not $cfg.ContainsKey($sec) -or -not $cfg[$sec].ContainsKey($key) -or $cfg[$sec][$key] -eq '') {
            throw "配置文件缺少 [$sec] 下的 $key（或为空），请检查 $Path"
        }
    }

    # 补默认值
    if ($cfg.ContainsKey('monitor')) {
        if (-not $cfg['monitor'].ContainsKey('test_ip'))    { $cfg['monitor']['test_ip']    = '223.5.5.5' }
        if (-not $cfg['monitor'].ContainsKey('delay'))      { $cfg['monitor']['delay']      = '16' }
        if (-not $cfg['monitor'].ContainsKey('max_failed')) { $cfg['monitor']['max_failed'] = '3' }
    } else {
        $cfg['monitor'] = @{ test_ip = '223.5.5.5'; delay = '16'; max_failed = '3' }
    }
    if (-not $cfg['account'].ContainsKey('domain')) { $cfg['account']['domain'] = '@dx' }

    return $cfg
}

# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

function Invoke-HttpGet {
    <#  GET 并返回响应正文；4xx/5xx 也尽量把正文取回来（srun 会用错误码表达业务失败）  #>
    param([string]$Url)

    try {
        $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -UserAgent $script:UserAgent -TimeoutSec 15
        return $r.Content
    }
    catch {
        $resp = $_.Exception.Response
        if ($null -ne $resp) {
            $sr = New-Object System.IO.StreamReader($resp.GetResponseStream())
            try   { return $sr.ReadToEnd() }
            finally { $sr.Dispose() }
        }
        throw
    }
}

# ---------------------------------------------------------------------------
# 登录流程 —— 移植自 BitSrunLogin/LoginManager.py
# ---------------------------------------------------------------------------

function Get-LoginIp {
    <#
      取本机在 srun 侧看到的 IP。
      登录页可能只是一个 <meta http-equiv="refresh"> 跳转壳（requests 和 Invoke-WebRequest 都不会自动跟随），
      所以要先手动跟到真正的 portal 页；再兼容新旧两种页面格式。
    #>
    param([hashtable]$Config)

    $base = $Config['portal']['url'].TrimEnd('/')
    $html = Invoke-HttpGet "$base/"

    $m = [regex]::Match($html, 'http-equiv="refresh"[^>]*url=([^"''>\s]+)', 'IgnoreCase')
    if ($m.Success) {
        $url = $m.Groups[1].Value -replace '&amp;', '&'
        if (-not $url.StartsWith('http')) { $url = $base + $url }
        $html = Invoke-HttpGet $url
    }

    # 新 portal：JS 里的 var CONFIG = { ... ip: "10.20.8.115" ... }
    $m = [regex]::Match($html, '\bip\s*:\s*["'']([\d.]+)["'']')
    if ($m.Success) { return $m.Groups[1].Value }

    # 老 portal：隐藏 input
    $m = [regex]::Match($html, 'id="user_ip" value="([\d.]+)"')
    if ($m.Success) { return $m.Groups[1].Value }

    throw 'Cannot find local ip in login page html, maybe the srun portal is updated'
}

function Get-ChallengeToken {
    <#  向 srun 申请本次登录的 challenge token  #>
    param([string]$Username, [string]$Ip, [string]$Base)

    $q = 'callback=jsonp1583251661367' +
         '&username=' + [uri]::EscapeDataString($Username) +
         '&ip='       + [uri]::EscapeDataString($Ip)
    $txt = Invoke-HttpGet "$Base/cgi-bin/get_challenge?$q"

    $m = [regex]::Match($txt, '"challenge":"(.*?)"')
    if (-not $m.Success) { throw "Failed to resolve token from challenge response: $txt" }
    return $m.Groups[1].Value
}

function ConvertTo-JsonString {
    <#  把一个字符串转义成 JSON 字符串字面量（含引号）  #>
    param([string]$Value)

    $esc = $Value.Replace('\', '\\').Replace('"', '\"')
    return '"' + $esc + '"'
}

function New-LoginInfo {
    <#
      构造待加密的 info 串。
      键序必须与 Python 参考实现一致：username, password, ip, acid, enc_ver，且不能有空格。
    #>
    param([string]$Username, [string]$Password, [string]$Ip, [string]$AcId)

    return '{"username":' + (ConvertTo-JsonString $Username) +
           ',"password":'  + (ConvertTo-JsonString $Password) +
           ',"ip":'        + (ConvertTo-JsonString $Ip) +
           ',"acid":'      + (ConvertTo-JsonString $AcId) +
           ',"enc_ver":'   + (ConvertTo-JsonString $script:SrunEnc) + '}'
}

function Invoke-SrunLogin {
    <#  完整登录流程  #>
    param(
        [hashtable]$Config,
        [switch]$Quiet
    )

    $say = { param($msg) if (-not $Quiet) { Write-Host $msg } }

    $base     = $Config['portal']['url'].TrimEnd('/')
    $acId     = [string]$Config['portal']['ac_id']
    $username = [string]$Config['account']['username'] + [string]$Config['account']['domain']
    $password = [string]$Config['account']['password']

    # Step1: 取 IP
    & $say 'Step1: Get local ip returned from srun server.'
    $ip = Get-LoginIp -Config $Config
    & $say "  local ip = $ip"

    # Step2: 取 token
    & $say 'Step2: Get token by resolving challenge result.'
    $token = Get-ChallengeToken -Username $username -Ip $ip -Base $base

    # Step3: 加密并登录
    & $say 'Step3: Loggin and resolve response.'
    $info          = New-LoginInfo -Username $username -Password $password -Ip $ip -AcId $acId
    $encryptedInfo = '{SRBX1}' + (Get-SrunBase64 (Get-XEncode -Message $info -Key $token))
    $md5           = Get-HmacMd5 -Key $token -Message $password
    $encryptedMd5  = '{MD5}' + $md5

    $chkstr = $token + $username +
              $token + $md5 +
              $token + $acId +
              $token + $ip +
              $token + $script:SrunN +
              $token + $script:SrunVType +
              $token + $encryptedInfo
    $chkstrEnc = Get-Sha1 $chkstr

    $q = 'callback=jQuery112407481914773997063_1631531125398' +
         '&action=login' +
         '&username=' + [uri]::EscapeDataString($username) +
         '&password=' + [uri]::EscapeDataString($encryptedMd5) +
         '&ac_id='    + [uri]::EscapeDataString($acId) +
         '&ip='       + [uri]::EscapeDataString($ip) +
         '&chksum='   + [uri]::EscapeDataString($chkstrEnc) +
         '&info='     + [uri]::EscapeDataString($encryptedInfo) +
         '&n='        + [uri]::EscapeDataString($script:SrunN) +
         '&type='     + [uri]::EscapeDataString($script:SrunVType) +
         '&os='       + [uri]::EscapeDataString('Windows 10') +
         '&name='     + [uri]::EscapeDataString('Windows') +
         '&double_stack=0'

    $resp = Invoke-HttpGet "$base/cgi-bin/srun_portal?$q"
    & $say $resp

    $m = [regex]::Match($resp, '"error":"(.*?)"')
    if (-not $m.Success) { throw "Cannot resolve login result. Maybe the srun response format is changed: $resp" }

    $result = $m.Groups[1].Value
    & $say "The loggin result is: $result"
    return $result
}

# ---------------------------------------------------------------------------
# 守护循环 —— 对应 always_online.py
# ---------------------------------------------------------------------------

function Write-UestcLog {
    param([string]$Message)

    $stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $line  = "[$stamp] $Message"
    Write-Host $line

    $dir = Join-Path $PSScriptRoot 'logs'
    if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    Add-Content -LiteralPath (Join-Path $dir 'uestc-login.log') -Value $line -Encoding UTF8
}

function Test-InternetConnection {
    param([string]$Target, [int]$TimeoutMs = 1000)

    & ping.exe -n 1 -w $TimeoutMs $Target *> $null
    return ($LASTEXITCODE -eq 0)
}

function Start-Monitor {
    param([hashtable]$Config)

    $testIp    = $Config['monitor']['test_ip']
    $delay     = [int]$Config['monitor']['delay']
    $maxFailed = [int]$Config['monitor']['max_failed']
    $orgDelay  = $delay
    $failed    = 0
    $wasOffline = $false
    # 掉线时缩短探测间隔以便尽快重连，但不能无下限地衰减到 0：
    # 衰减到 0 就变成不留间隔的死循环，会一秒一发地打认证服务器。
    $minDelay  = [int][math]::Max(2, $orgDelay / 8)

    Write-UestcLog "网络监控启动 (test_ip=$testIp, delay=${delay}s, max_failed=$maxFailed)"

    while ($true) {
        if (-not (Test-InternetConnection -Target $testIp)) {
            $failed++
            if ($failed -ge $maxFailed) {
                Write-UestcLog '检测到断网，尝试重新登录...'
                try {
                    $r = Invoke-SrunLogin -Config $Config -Quiet
                    Write-UestcLog "重新登录结果: $r"
                }
                catch {
                    Write-UestcLog "登录失败: $($_.Exception.Message)"
                }
                # 已经尝试过一次登录了：重新计数并回到正常间隔。
                # 不这样做的话，只要探测点本身一直不通（典型情况是该 IP 屏蔽 ICMP，
                # 或它根本不在校园网放行列表里），delay 就会停在最小值上无限重试。
                $wasOffline = $true
                $failed     = 0
                $delay      = $orgDelay
            }
            else {
                $delay = [int][math]::Max($minDelay, $delay / 2)
            }
        }
        else {
            if ($wasOffline) {
                Write-UestcLog '已恢复在线。'
                $wasOffline = $false
            }
            $failed = 0
            $delay  = $orgDelay
        }
        Start-Sleep -Seconds $delay
    }
}

# ---------------------------------------------------------------------------
# 自检
# ---------------------------------------------------------------------------

function Invoke-SelfTest {
    <#  用 Python 参考实现采集的黄金向量校验加密移植是否逐字节一致  #>

    $fail = 0

    function Assert-Equal {
        param([string]$Name, $Expected, $Actual)
        if ("$Expected" -eq "$Actual") {
            Write-Host ("  [OK]   {0}" -f $Name) -ForegroundColor Green
        }
        else {
            Write-Host ("  [FAIL] {0}`n         期望: {1}`n         实际: {2}" -f $Name, $Expected, $Actual) -ForegroundColor Red
            $script:__fail++
        }
    }
    $script:__fail = 0

    Write-Host 'SrunBase64:'
    Assert-Equal 'base64("132456")' '9F9x0JHI' (Get-SrunBase64 ([Text.Encoding]::UTF8.GetBytes('132456')))

    Write-Host 'HmacMd5 / Sha1:'
    Assert-Equal 'hmac_md5("pw")' '5bc328079a5dc482a40824390b37063f' (Get-HmacMd5 -Key $script:TestKey -Message 'pw')
    Assert-Equal 'sha1("hello")'  'aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d' (Get-Sha1 'hello')

    Write-Host 'XEncode (XXTEA):'
    $xe = Get-XEncode -Message $script:TestMsg -Key $script:TestKey
    Assert-Equal 'xencode 长度' 96 $xe.Length
    $head = ($xe[0..11] -join ',')
    Assert-Equal 'xencode 前12字节' '22,212,163,47,163,1,117,23,205,77,65,182' $head
    Assert-Equal 'xencode + base64' 'ifmkGB9Vnhs0FHCIQZnATcecSSGyJulOcgodsvw3yrlMkXHH8K89aWgIPjkKlk8FH5TISo3NLpkQa7SaK0dkiodLIWXbUB8bMTf99+lOCH0jD5XuXVWTuvuQEyaBOxY0' (Get-SrunBase64 $xe)

    Write-Host ''
    if ($script:__fail -eq 0) {
        Write-Host '全部通过，加密移植与 Python 参考实现逐字节一致。' -ForegroundColor Green
        return $true
    }
    Write-Host "$($script:__fail) 项失败。" -ForegroundColor Red
    return $false
}

# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

if ($SelfTest) {
    $ok = Invoke-SelfTest
    exit ([int](-not $ok))
}

$cfg = Read-UestcConfig -Path $ConfigPath

if ($Daemon) {
    Start-Monitor -Config $cfg
}
else {
    Invoke-SrunLogin -Config $cfg | Out-Null
}
