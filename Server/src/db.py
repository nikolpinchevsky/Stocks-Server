import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
_client = None

def get_db():
    global _client
    uri = os.getenv("MONGO_URI")
    db_name = os.getenv("DB_NAME", "stockdb")
    if not uri:
        raise RuntimeError("MONGO_URI missing in .env")

    if _client is None:
        _client = MongoClient(uri)

    return _client[db_name]
