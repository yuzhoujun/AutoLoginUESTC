"""
校验和（chksum）字段的计算。

本文件的代码来自参考实现，逻辑未做修改，仅补充注释。
"""
import hashlib


def get_sha1(value):
    """
    计算 SHA1，返回 40 位小写十六进制字符串。

    调用方（LoginManager._generate_chksum）按固定顺序把 token 与各字段依次
    拼接后再传入，顺序错则该值不匹配，认证服务器会直接拒绝登录。
    """
    return hashlib.sha1(value.encode()).hexdigest()


if __name__ == '__main__':
    print(get_sha1("123456"))
