"""
XXTEA 加密（深澜变体），用于加密登录请求中的 info 字段。

本文件的代码来自参考实现，逻辑未做修改，仅补充注释。

背景
----
XXTEA 是分组加密算法，以 32 位无符号整数为单位运算。原实现里到处出现的
`0x8CE0D9BF | 0x731F2640` 这类常量看起来像是随机数，实际上全都是
**0xFFFFFFFF**，只是被拆成两个数按位或的形式写出来（这种写法常见于经过
混淆的 JavaScript 代码）。同理，轮增量 `c` 的 `0x86014019 | 0x183639A0`
就是 XXTEA 的标准 delta 值 **0x9E3779B9**。

数据流
------
    get_xencode(msg, key)
        ├─ sencode(msg, True)   消息 -> 32 位字列表（末尾追加原始长度）
        ├─ sencode(key, False)  密钥 -> 32 位字列表（不追加长度）
        ├─ 32 轮轮询混淆
        └─ lencode(pwd, False)  32 位字列表 -> 字符串

注意：Python 的整数不会溢出，按位运算天然就是 32 位语义，因此本文件不需要
像其他语言的移植版本那样显式地做 `& 0xFFFFFFFF` 截断。
"""
import math


def ordat(msg, idx):
    """取 msg[idx] 的字符编码；越界时返回 0（相当于按 0 填充）。"""
    if len(msg) > idx:
        return ord(msg[idx])
    return 0


def sencode(msg, key):
    """
    把字符串按 4 字符一组、小端序打包成 32 位整数列表。

    key 为真时在末尾追加消息的原始长度。XXTEA 要求对**消息**追加长度
    （避免尾部填充被截断），对**密钥**不追加，所以两处调用的取值不同。
    """
    l = len(msg)
    pwd = []
    for i in range(0, l, 4):
        pwd.append(
            ordat(msg, i) | ordat(msg, i + 1) << 8 | ordat(msg, i + 2) << 16
            | ordat(msg, i + 3) << 24)
    if key:
        pwd.append(l)
    return pwd


def lencode(msg, key):
    """
    sencode 的逆操作：把 32 位整数列表拆回字符串，每个整数输出 4 个小端字节。

    key 为真时按末尾那个整数截断（还原 sencode 追加的原始长度）；此处调用
    传的是 False，因为加密结果需要完整的字节串。
    """
    l = len(msg)
    ll = (l - 1) << 2
    if key:
        m = msg[l - 1]
        if m < ll - 3 or m > ll:
            return
        ll = m
    for i in range(0, l):
        msg[i] = chr(msg[i] & 0xff) + chr(msg[i] >> 8 & 0xff) + chr(
            msg[i] >> 16 & 0xff) + chr(msg[i] >> 24 & 0xff)
    if key:
        return "".join(msg)[0:ll]
    return "".join(msg)


def get_xencode(msg, key):
    """
    XXTEA 加密入口。key 为 challenge token，msg 为待加密的 info 字符串。

    轮数为 6 + 52/(n+1) 向下取整，其中 n 是 32 位字的个数。
    返回值是密文的原始字节串；调用方还需再做一次自定义 base64，并加上
    "{SRBX1}" 前缀，才能作为请求参数发出。
    """
    if msg == "":
        return ""
    pwd = sencode(msg, True)
    pwdk = sencode(key, False)
    if len(pwdk) < 4:
        # 密钥不足 4 个字时补零，保证后面的 pwdk[(p & 3) ^ e] 取值不出界
        pwdk = pwdk + [0] * (4 - len(pwdk))
    n = len(pwd) - 1
    z = pwd[n]
    y = pwd[0]
    c = 0x86014019 | 0x183639A0  # = 0x9E3779B9，XXTEA 标准 delta
    m = 0
    e = 0
    p = 0
    q = math.floor(6 + 52 / (n + 1))  # 轮数，随消息长度变化
    d = 0
    while 0 < q:
        d = d + c & (0x8CE0D9BF | 0x731F2640)  # 掩码即 0xFFFFFFFF
        e = d >> 2 & 3
        p = 0
        while p < n:
            y = pwd[p + 1]
            m = z >> 5 ^ y << 2
            m = m + ((y >> 3 ^ z << 4) ^ (d ^ y))
            m = m + (pwdk[(p & 3) ^ e] ^ z)
            pwd[p] = pwd[p] + m & (0xEFB8D130 | 0x10472ECF)  # 掩码即 0xFFFFFFFF
            z = pwd[p]
            p = p + 1
        # 每一轮结束后补做一次，把最后一个字和第一个字串起来（XXTEA 的循环结构）
        y = pwd[0]
        m = z >> 5 ^ y << 2
        m = m + ((y >> 3 ^ z << 4) ^ (d ^ y))
        m = m + (pwdk[(p & 3) ^ e] ^ z)
        pwd[n] = pwd[n] + m & (0xBB390742 | 0x44C6F8BD)  # 掩码即 0xFFFFFFFF
        z = pwd[n]
        q = q - 1
    return lencode(pwd, False)


if __name__ == '__main__':
    # 自测：用固定输入验证加密结果。get_xencode 返回的是字符串（lencode 用 chr()
    # 逐字节拼出来的），所以取字节值要过一道 ord()。
    # 完整的加密自检（含 base64 / HMAC-MD5 / SHA1）见项目根目录的 selftest.py。
    _key = "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789"
    _msg = '{"username":"1234567890@dx","password":"pw","ip":"10.0.0.1","acid":"3","enc_ver":"srun_bx1"}'
    _out = get_xencode(_msg, _key)
    _head = [ord(c) for c in _out[:12]]
    print('length =', len(_out))
    print('head   =', _head)
    assert len(_out) == 96, f'期望长度 96，实际 {len(_out)}'
    assert _head == [22, 212, 163, 47, 163, 1, 117, 23, 205, 77, 65, 182], '首字节不匹配'
    print('OK')
