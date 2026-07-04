import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken


def _fernet(jwt_secret: str) -> Fernet:
    key = base64.urlsafe_b64encode(hashlib.sha256(jwt_secret.encode()).digest())
    return Fernet(key)


def encrypt_password(plain: str, jwt_secret: str) -> str:
    return _fernet(jwt_secret).encrypt(plain.encode()).decode()


def decrypt_password(encrypted: str, jwt_secret: str) -> str | None:
    if not encrypted:
        return None
    try:
        return _fernet(jwt_secret).decrypt(encrypted.encode()).decode()
    except InvalidToken:
        return None
