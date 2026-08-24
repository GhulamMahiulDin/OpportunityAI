"""
Small helper around Fernet symmetric encryption, used to store Gmail
OAuth tokens in the database without keeping them in plain text.
"""
from cryptography.fernet import Fernet
from flask import current_app


def _get_fernet():
    key = current_app.config['TOKEN_ENCRYPTION_KEY']
    if isinstance(key, str):
        key = key.encode('utf-8')
    return Fernet(key)


def encrypt_text(plain_text):
    """Encrypts a string, returns a string safe to store in a TEXT column."""
    f = _get_fernet()
    return f.encrypt(plain_text.encode('utf-8')).decode('utf-8')


def decrypt_text(cipher_text):
    """Decrypts a string previously produced by encrypt_text()."""
    f = _get_fernet()
    return f.decrypt(cipher_text.encode('utf-8')).decode('utf-8')
