import hashlib

def new(key, msg, digestmod):
    """
    Minimal HMAC implementation.
    """
    block_size = 64 # for sha256
    
    if len(key) > block_size:
        key = digestmod(key).digest()
    if len(key) < block_size:
        key = key + b'\x00' * (block_size - len(key))
        
    o_key_pad = bytes(x ^ 0x5c for x in key)
    i_key_pad = bytes(x ^ 0x36 for x in key)
    
    return HMAC(o_key_pad, i_key_pad, digestmod, msg)

class HMAC:
    def __init__(self, o_key, i_key, digestmod, msg):
        self.o_key = o_key
        self.i_key = i_key
        self.digestmod = digestmod
        self.inner = digestmod(i_key)
        self.inner.update(msg)
        
    def digest(self):
        inner_hash = self.inner.digest()
        outer = self.digestmod(self.o_key)
        outer.update(inner_hash)
        return outer.digest()
