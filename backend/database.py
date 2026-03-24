import os
from typing import Any

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase


load_dotenv()

MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME")

if not MONGO_URL or not DB_NAME:
    raise RuntimeError("MONGO_URL and DB_NAME must be configured.")

client = AsyncIOMotorClient(MONGO_URL)
database: AsyncIOMotorDatabase = client[DB_NAME]


def clean_document(document: dict[str, Any] | None) -> dict[str, Any] | None:
    if not document:
        return document
    cleaned = {key: value for key, value in document.items() if key != "_id"}
    return cleaned
