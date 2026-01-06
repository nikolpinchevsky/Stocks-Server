import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables (like MONGO_URI) from the .env file
load_dotenv()

# Global variable to store the active MongoDB connection
# We use this to ensure we connect only once (Singleton pattern)
_client = None


# Establishes or retrieves the connection to the MongoDB database
# 1. Reads the URI from environment variables
# 2. Connects to the cloud database
# 3. Returns the specific database object
def get_db():
    global _client

    # Get the connection string and database name from .env
    uri = os.getenv("MONGO_URI")
    db_name = os.getenv("DB_NAME", "stockdb")

    # Safety check: ensure the URI exists
    if not uri:
        raise RuntimeError("MONGO_URI missing in .env")

    # Connect only if a connection doesn't exist yet (Lazy Loading)
    if _client is None:
        _client = MongoClient(uri)

    # Return the specific database object
    return _client[db_name]
