# The MIT License (MIT)
# Copyright © 2023 Rapiiidooo
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the “Software”), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.
#
# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
import hashlib
import random
import secrets
import base64
import bittensor as bt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

import compute


def gen_hash(mode: str, password, salt=None):
    # check the mode selection for the hash
    if mode == '8900': # For Scrypt
        salt = secrets.token_bytes(24) if salt is None else base64.b64decode(salt.encode("utf-8"))
        password_bytes = password.encode('ascii')
        hashed_password = hashlib.scrypt(password_bytes, salt=salt, n=1024, r=1, p=1, dklen=32)
        hash_result = str(base64.b64encode(hashed_password).decode('utf-8'))
        salt = str(base64.b64encode(salt).decode('utf-8'))
        return f"SCRYPT:1024:1:1:{hash_result}", salt
    elif mode== '610' or mode== '1410' or mode== '10810' or mode== '1710':  # For Blake2b-512, SHA-256, SHA-384, SHA-512
        salt = secrets.token_hex(8) if salt is None else salt
        salted_password = password + salt
        data = salted_password.encode("utf-8")
        padding = ""
        if mode == '610':
            hash_result = hashlib.blake2b(data).hexdigest()
            padding = "$BLAKE2$"
        elif mode == '1410':
            hash_result = hashlib.sha256(data).hexdigest()
        elif mode == '10810':
            hash_result = hashlib.sha384(data).hexdigest()
        elif mode == '1710':
            hash_result = hashlib.sha512(data).hexdigest()
        return f"{padding}{hash_result}", salt
    else:
        bt.logging.error("Not recognized hash mode")
        return


def gen_random_string(available_chars=compute.pow_default_chars, length=compute.pow_min_difficulty):
    # Generating private/public keys
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    # Using the private key bytes as seed for guaranteed randomness
    seed = int.from_bytes(private_bytes, "big")
    random.seed(seed)
    return "".join(random.choice(available_chars) for _ in range(length))


def gen_password(mode: str, available_chars=compute.pow_default_chars, length=compute.pow_min_difficulty):
    try:
        password = gen_random_string(available_chars=available_chars, length=length)
        _mask = "".join(["?1" for _ in range(length)])
        _hash, _salt = gen_hash(mode, password)
        return password, _hash, _salt, _mask
    except Exception as e:
        bt.logging.error(f"Error during PoW generation (gen_password): {e}")
        return None


def run_validator_pow(mode: str, length=compute.pow_min_difficulty):
    """
    Don't worry this function is fast enough for validator to use CPUs
    """
    available_chars = compute.pow_default_chars
    available_chars = list(available_chars)
    random.shuffle(available_chars)
    available_chars = "".join(available_chars)
    password, _hash, _salt, _mask = gen_password(mode=mode, available_chars=available_chars[:10], length=length)
    # Change from default mode to return the selected random mode back
    return password, _hash, _salt, mode, available_chars[:10], _mask