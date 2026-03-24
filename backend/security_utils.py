import base64
import hashlib
import os

from cryptography.fernet import Fernet
from dotenv import load_dotenv


load_dotenv()


def _build_fernet() -> Fernet:
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME")

    if not mongo_url or not db_name:
        raise RuntimeError("MONGO_URL and DB_NAME must be configured for provider key encryption.")

    digest = hashlib.sha256(f"{mongo_url}|{db_name}|provider-key-storage-v1".encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


FERNET = _build_fernet()


def encrypt_secret(value: str) -> str:
    return FERNET.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str) -> str:
    return FERNET.decrypt(value.encode("utf-8")).decode("utf-8")