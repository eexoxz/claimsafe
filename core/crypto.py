from cryptography.fernet import Fernet, MultiFernet
from django.conf import settings


def field_cipher():
    return MultiFernet([Fernet(key) for key in [settings.FIELD_ENCRYPTION_KEY, *settings.FIELD_ENCRYPTION_FALLBACK_KEYS]])


def encrypt_text(value):
    return field_cipher().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_text(value):
    return field_cipher().decrypt(value.encode("ascii")).decode("utf-8") if value else ""
