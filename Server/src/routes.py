import os
import time
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from passlib.hash import bcrypt
import jwt
from dotenv import load_dotenv
from .db import get_db

# Load environment variables (DB URI, Secrets) from the .env file
load_dotenv()
JWT_SECRET = os.getenv("JWT_SECRET", "change_me")

router = APIRouter()

# Security scheme: Extract the Bearer token from the Authorization header
bearer = HTTPBearer(auto_error=True)


# ============== Data Models ==============

# Model for user registration and login credentials
class AuthBody(BaseModel):
    email: str
    password: str

# Model for adding a stock symbol to the watchlist
class WatchBody(BaseModel):
    symbol: str

# Model for seeding or updating stock metadata
# 'price' is optional to allow creating a stock before price data is available
class StockUpsertBody(BaseModel):
    symbol: str
    name: str | None = None
    price: float | None = None
    currency: str = "USD"

# Represents a single data point (timestamp, price, volume) in the chart history
class HistoryPoint(BaseModel):
    ts: int          
    price: float
    volume: int

# Model for uploading a complete history list for a specific stock
class StockHistoryBody(BaseModel):
    symbol: str
    points: list[HistoryPoint]



# ============== Helper Functions ==============

# Generates a JWT token for the authenticated user
# Token is valid for 7 days
def create_token(user_id: str) -> str:
    payload = {"uid": user_id, "exp": int(time.time()) + 60 * 60 * 24 * 7}
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

# Dependency to protect routes
# Validates the JWT token and returns the User ID (uid)
# Raises 401 if the token is invalid or expired
def require_user(creds: HTTPAuthorizationCredentials = Depends(bearer)) -> str:
    token = creds.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload["uid"]
    except Exception:
        raise HTTPException(status_code=401, detail="invalid token")

# Standardizes stock symbols (e.g., converts ' nike ' to 'NIKE')
# Ensures consistency across the database
def norm_symbol(symbol: str) -> str:
    s = (symbol or "").upper().strip()
    if not s:
        raise HTTPException(status_code=400, detail="symbol required")
    return s


# ============== Routes ==============

# Simple health check to verify the server is running
@router.get("/health")
def health():
    return {"status": "ok"}

# Registers a new user
# 1. Verifies email uniqueness
# 2. Hashes the password using bcrypt
# 3. Initializes an empty watchlist for the user
@router.post("/auth/register")
def register(body: AuthBody):
    db = get_db()
    users = db["users"]

    email = body.email.strip().lower()
    if not email or not body.password:
        raise HTTPException(status_code=400, detail="email/password required")

    if users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="email exists")

    hashed = bcrypt.hash(body.password)
    res = users.insert_one({"email": email, "password": hashed, "createdAt": int(time.time())})
    uid = str(res.inserted_id)

    db["watchlists"].insert_one({"userId": uid, "symbols": []})

    return {"token": create_token(uid)}

# Authenticates a user
# Checks email existence and verifies password hash
# Returns a JWT access token
@router.post("/auth/login")
def login(body: AuthBody):
    db = get_db()
    users = db["users"]

    email = body.email.strip().lower()
    u = users.find_one({"email": email})
    if not u or not bcrypt.verify(body.password, u["password"]):
        raise HTTPException(status_code=401, detail="invalid credentials")

    return {"token": create_token(str(u["_id"]))}


# ============== Stocks Management ==============

# Admin endpoint to create or update stock details
# Uses 'upsert=True' to handle both creation and updates in one request
@router.post("/stocks/seed")
def upsert_stock(body: StockUpsertBody, uid: str = Depends(require_user)):
    db = get_db()
    symbol = norm_symbol(body.symbol)

    update_doc = {
        "symbol": symbol,
        "name": body.name,
        "currency": body.currency or "USD",
        "updatedAt": int(time.time())
    }

    if body.price is not None:
        update_doc["price"] = body.price

    db["stocks"].update_one(
        {"symbol": symbol},
        {"$set": update_doc},
        upsert=True
    )

    return {"ok": True, "symbol": symbol}

# Returns a list of all available stocks, sorted by symbol
@router.get("/stocks")
def list_stocks(uid: str = Depends(require_user)):
    db = get_db()
    items = list(db["stocks"].find({}, {"_id": 0}).sort("symbol", 1))
    return {"items": items}

# Fetches the current price and details for a specific stock
@router.get("/stocks/{symbol}/quote")
def quote(symbol: str, uid: str = Depends(require_user)):
    db = get_db()
    symbol = norm_symbol(symbol)

    doc = db["stocks"].find_one({"symbol": symbol}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="symbol not found in DB")

    return {
        "symbol": doc["symbol"],
        "name": doc.get("name", ""),
        "c": float(doc.get("price", 0.0) or 0.0),
        "currency": doc.get("currency", "USD"),
        "updatedAt": doc.get("updatedAt"),
        "source": "mongodb"
    }


# ============== History & Charts ==============

# Updates the historical data for a stock
# IMPORTANT: Sorts the points by timestamp to ensure the chart renders correctly
@router.post("/stocks/history")
def upsert_history(body: StockHistoryBody, uid: str = Depends(require_user)):
    db = get_db()
    symbol = norm_symbol(body.symbol)

    points = sorted([p.model_dump() for p in body.points], key=lambda x: x["ts"])

    db["stock_history"].update_one(
        {"symbol": symbol},
        {"$set": {
            "symbol": symbol,
            "points": points,
            "updatedAt": int(time.time())
        }},
        upsert=True
    )

    return {"ok": True, "symbol": symbol, "count": len(points)}

# Retrieves historical points for charting
# Returns points sorted chronologically
@router.get("/stocks/{symbol}/history")
def get_history(symbol: str, uid: str = Depends(require_user)):
    db = get_db()
    symbol = norm_symbol(symbol)

    doc = db["stock_history"].find_one({"symbol": symbol}, {"_id": 0})
    if not doc:
        return {"symbol": symbol, "points": []}

    pts = sorted(doc.get("points", []), key=lambda x: x.get("ts", 0))
    return {"symbol": symbol, "points": pts, "updatedAt": doc.get("updatedAt")}

# Appends a single historical data point to an existing stock's history
@router.post("/stocks/{symbol}/history/append")
def append_history_point(symbol: str, point: HistoryPoint, uid: str = Depends(require_user)):
    db = get_db()
    symbol = norm_symbol(symbol)

    db["stock_history"].update_one(
        {"symbol": symbol},
        {"$push": {"points": point.model_dump()}, "$set": {"updatedAt": int(time.time())}},
        upsert=True
    )
    return {"ok": True, "symbol": symbol}



# ============== Watchlist ==============

# Retrieves the list of tracked stocks for the current user
@router.get("/watchlist")
def get_watchlist(uid: str = Depends(require_user)):
    db = get_db()
    wl = db["watchlists"].find_one({"userId": uid}) or {"symbols": []}
    return {"symbols": wl.get("symbols", [])}

# Adds a stock to the user's watchlist
# Uses '$addToSet' to prevent duplicate entries
@router.post("/watchlist")
def add_watch(body: WatchBody, uid: str = Depends(require_user)):
    symbol = norm_symbol(body.symbol)

    db = get_db()
    db["watchlists"].update_one(
        {"userId": uid},
        {"$addToSet": {"symbols": symbol}},
        upsert=True
    )
    return {"ok": True, "symbol": symbol}

# Removes a stock from the user's watchlist
@router.delete("/watchlist/{symbol}")
def remove_watch(symbol: str, uid: str = Depends(require_user)):
    db = get_db()
    symbol = norm_symbol(symbol)

    db["watchlists"].update_one(
        {"userId": uid},
        {"$pull": {"symbols": symbol}},
        upsert=True
    )
    return {"ok": True}
