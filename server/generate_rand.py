# code verifier について
# 使用可能文字種：半角英数字（a〜z、A～Z、0～9）および記号（-._~）からなるランダムな文字列
# 文字数：43文字〜128文字

# code_challenge (S256)について
# code_verifierをSHA256で暗号化したうえで、Base64URL形式にエンコードした値
# ただし、URLクエリパラメタとしてできるようにするには、
# 通常のBase64形式の文字列から以下の3つの置換を行う必要がある。
# パディング(文字詰めの=) -> 削除
# + -> -
# / -> _
# 例
# 変換前 BSCQwo_m8Wf0fpjmwk+KmPAJ1A/tiuRSNDnXzODS7==	
# 変換後 BSCQwo_m8Wf0fpjmwk-KmPAJ1A_tiuRSNDnXzODS7
import hashlib
import secrets
import base64

def generate_code_verifier(length: int = 128) -> str:
    if not 43 <= length <= 128:
        msg = 'Parameter `length` must verify `43 <= length <= 128`.'
        raise ValueError(msg)
    code_verifier = secrets.token_urlsafe(96)[:length]
    return code_verifier

def get_urlsafe_code_challenge(code_verifier: str) -> str:
    if not 43 <= len(code_verifier) <= 128:
        msg = 'Parameter `code_verifier` must verify '
        msg += '`43 <= len(code_verifier) <= 128`.'
        raise ValueError(msg)
    hashed = hashlib.sha256(code_verifier.encode('ascii')).digest()
    encoded = base64.urlsafe_b64encode(hashed)
    code_challenge = encoded.decode('ascii')[:-1]
    return code_challenge

# stateについて
# 長さに制限はない
# https://auth0.com/docs/secure/attack-protection/state-parameters#set-and-compare-state-parameter-values

def generate_state(length: int = 32) -> str:
    if not 4 <= length <= 128: # なんとなく
        msg = 'Parameter `length` must verify `43 <= length <= 128`.'
        raise ValueError(msg)
    state = secrets.token_urlsafe(96)[:length]
    return state