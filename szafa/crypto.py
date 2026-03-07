from cryptography.fernet import Fernet
from django.conf import settings


fernet = Fernet(settings.FIELD_ENCRYPTION_KEY)


def encrypt_value(value: str):

    if not value:
        return value

    return fernet.encrypt(value.encode()).decode()


def decrypt_value(value: str):

    if not value:
        return value

    return fernet.decrypt(value.encode()).decode()