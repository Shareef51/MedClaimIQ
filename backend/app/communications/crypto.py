from __future__ import annotations

import base64
import hashlib
import hmac
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class DestinationCipher:
    """Envelope-like application encryption for communication destinations.

    Production deployments should source the secret from KMS/secret manager and
    rotate key_version. Ciphertext is never returned by public APIs.
    """
    def __init__(self, secret:str, *, key_version:str="v1"):
        if len(secret) < 32: raise ValueError("communication destination encryption secret must be at least 32 characters")
        self._raw=secret.encode("utf-8"); self._key=hashlib.sha256(self._raw).digest(); self.key_version=key_version

    def encrypt(self,value:str)->str:
        nonce=os.urandom(12); ciphertext=AESGCM(self._key).encrypt(nonce,value.encode("utf-8"),None)
        return base64.urlsafe_b64encode(nonce+ciphertext).decode("ascii")

    def decrypt(self,value:str)->str:
        raw=base64.urlsafe_b64decode(value.encode("ascii")); return AESGCM(self._key).decrypt(raw[:12],raw[12:],None).decode("utf-8")

    def fingerprint(self,value:str)->str:
        return hmac.new(self._raw,value.strip().lower().encode("utf-8"),hashlib.sha256).hexdigest()
