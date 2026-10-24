from cryptography.fernet import Fernet
from django.conf import settings


def encrypt_text(value):
    return Fernet(settings.FIELD_ENCRYPTION_KEY).encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_text(value):
    return Fernet(settings.FIELD_ENCRYPTION_KEY).decrypt(value.encode("ascii")).decode("utf-8") if value else ""
