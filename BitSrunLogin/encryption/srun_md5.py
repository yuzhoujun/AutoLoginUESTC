"""
密码字段的摘要计算。

本文件的代码来自参考实现，逻辑未做修改，仅补充注释。
"""
import hmac
import hashlib
from urllib import parse


def get_md5(password, token):
    """
    计算登录请求中 password 字段的摘要，返回 32 位小写十六进制字符串。

    注意这是 **HMAC-MD5**，不是普通 MD5：以 challenge token 为密钥、以密码
    明文为消息。这一点很容易搞错 —— certutil 等工具只能算普通哈希，算不出
    这个值。函数名沿用参考实现的命名，实际语义是 HMAC。

    调用方还需在结果前加上 "{MD5}" 前缀，才能作为请求参数发出。
    """
    return hmac.new(token.encode(), password.encode(), hashlib.md5).hexdigest()


if __name__ == '__main__':
    password = "123"
    token = "8975424a6a063b318bb715f853a9e53fb4ea3f7dfff176624f202a5d1331a821"
    print(get_md5(password, token))
