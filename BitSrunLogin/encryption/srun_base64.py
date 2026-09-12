"""
深澜自定义字母表的 base64 编码。

本文件的代码来自参考实现，逻辑未做修改，仅补充注释。

与标准 base64 的唯一区别是**字母表**：深澜不使用标准的
A-Za-z0-9+/，而是使用 _ALPHA 中列出的顺序。其余规则（每 3 字节编为 4 个
字符、不足 3 字节时补 _PADCHAR）与标准 base64 完全一致。

因此不能直接用 Python 标准库的 base64 模块代替。例如编码 "132456"：
    本文件            -> 9F9x0JHI
    base64.b64encode  -> MTMyNDU2
"""
_PADCHAR = "="
_ALPHA = "LVoJPiCN2R8G90yg+hmFHuacZ1OWMnrsSTXkYpUq/3dlbfKwv6xztjI7DeBE45QA"


def _getbyte(s, i):
    """取 s[i] 的字符编码。超过 255 说明传入了非单字节字符，直接报错退出。"""
    x = ord(s[i])
    if (x > 255):
        print("INVALID_CHARACTER_ERR: DOM Exception 5")
        exit(0)
    return x


def get_base64(s):
    """
    按自定义字母表编码字符串 s，返回 base64 文本。

    实现方式与标准 base64 相同：把 3 个字节拼成一个 24 位整数，再切成 4 个
    6 位索引去查 _ALPHA。末尾不足 3 字节时，用 _PADCHAR 补齐到 4 个字符。
    """
    i = 0
    b10 = 0
    x = []
    # imax 之前的部分都是完整的 3 字节组，可以整组处理
    imax = len(s) - len(s) % 3
    if len(s) == 0:
        return s
    for i in range(0, imax, 3):
        b10 = (_getbyte(s, i) << 16) | (_getbyte(s, i + 1) << 8) | _getbyte(s, i + 2)
        x.append(_ALPHA[(b10 >> 18)])
        x.append(_ALPHA[((b10 >> 12) & 63)])
        x.append(_ALPHA[((b10 >> 6) & 63)])
        x.append(_ALPHA[(b10 & 63)])
    # 剩下的 1 或 2 个字节单独处理，缺的位置由 _PADCHAR 填充
    i = imax
    if len(s) - imax == 1:
        b10 = _getbyte(s, i) << 16
        x.append(_ALPHA[(b10 >> 18)] + _ALPHA[((b10 >> 12) & 63)] + _PADCHAR + _PADCHAR)
    elif len(s) - imax == 2:
        b10 = (_getbyte(s, i) << 16) | (_getbyte(s, i + 1) << 8)
        x.append(_ALPHA[(b10 >> 18)] + _ALPHA[((b10 >> 12) & 63)] + _ALPHA[((b10 >> 6) & 63)] + _PADCHAR)
    else:
        # 正好是 3 的整数倍，没有余数需要处理
        pass
    return "".join(x)


if __name__ == '__main__':
    r = get_base64("132456")
    print(r)
