# backend.py
"""
King Khufu Adventure Backend - Modernized, backward-compatible, production-ready
- Keeps original endpoints and behavior.
- Adds: Pydantic Settings, JWT auth, password hashing, escrow for auctions,
  async auction closing worker, Redis optional for cache/rate-limit/locks,
  atomic DB transactions, soft-delete marketplace, pagination, WebSocket updates.
"""

import os
import json
import logging
import asyncio
import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from collections import defaultdict

from fastapi import (
    FastAPI, HTTPException, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect, Request, Query
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings
from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, JSON, Boolean, func, Index, ForeignKey
)
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

# Security
from passlib.context import CryptContext
from jose import JWTError, jwt

# Optional Redis
try:
    import redis
    REDIS_AVAILABLE = True
except Exception:
    REDIS_AVAILABLE = False

# -------------------------
# Settings (Pydantic BaseSettings)
# -------------------------
class Settings(BaseSettings):
    database_url: str = "sqlite:///./khufu.db"
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    account_lock_threshold: int = 5
    account_lock_seconds: int = 300
    allow_origins: str = "http://localhost,http://127.0.0.1"
    redis_url: Optional[str] = None
    leaderboard_ttl: float = 3.0
    rate_limit_window: int = 10
    rate_limit_max: int = 20
    auction_worker_interval_seconds: int = 30

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

# -------------------------
# Logging
# -------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("khufu-backend")

# -------------------------
# Redis client (optional)
# -------------------------
redis_client = None
if REDIS_AVAILABLE and settings.redis_url:
    try:
        redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        redis_client.ping()
        logger.info("Connected to Redis at %s", settings.redis_url)
    except Exception as e:
        logger.warning("Redis connection failed: %s", e)
        redis_client = None

# -------------------------
# Database setup (SQLAlchemy)
# -------------------------
DATABASE_URL = settings.database_url
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    pool_pre_ping=True
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

# -------------------------
# ORM Models (preserve original fields + new fields)
# -------------------------
class PlayerDB(Base):
    __tablename__ = "players"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    coins = Column(Integer, default=0, index=True)
    level = Column(Integer, default=1, index=True)
    abilities = Column(JSON, default={})
    avatar = Column(String, default="default")
    outfit = Column(String, default="basic")
    achievements = Column(JSON, default=[])
    notifications = Column(JSON, default=[])
    hashed_password = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_players_level_coins", "level", "coins"),
    )

class MarketItemDB(Base):
    __tablename__ = "marketplace"
    id = Column(Integer, primary_key=True, index=True)
    seller = Column(String, nullable=False)
    item = Column(String, nullable=False)
    price = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_sold = Column(Boolean, default=False)            # soft-delete flag
    buyer = Column(String, nullable=True)                # buyer username if sold

class AuctionDB(Base):
    __tablename__ = "auctions"
    id = Column(Integer, primary_key=True, index=True)
    seller = Column(String, nullable=False)
    item = Column(String, nullable=False)
    base_price = Column(Integer, nullable=False)
    highest_bid = Column(Integer, nullable=False)
    highest_bidder = Column(String, nullable=True)
    end_time = Column(DateTime, nullable=False)
    closed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# Create tables if not exist
Base.metadata.create_all(bind=engine)

# -------------------------
# Pydantic Schemas
# -------------------------
class PaymentRequest(BaseModel):
    phone_number: str = Field(..., min_length=6)
    amount: float

    @validator("amount")
    def amount_positive(cls, v):
        if v <= 0:
            raise ValueError("المبلغ يجب أن يكون أكبر من صفر")
        return v

class PlayerCreate(BaseModel):
    username: str
    coins: int = 0
    level: int = 1
    abilities: Dict[str, bool] = {}
    avatar: str = "default"
    outfit: str = "basic"
    achievements: List[str] = []
    notifications: List[str] = []
    password: Optional[str] = None

class PlayerOut(BaseModel):
    username: str
    coins: int
    level: int
    abilities: Dict[str, bool]
    avatar: str
    outfit: str
    achievements: List[str]
    notifications: List[str]

class MarketItemIn(BaseModel):
    seller: str
    item: str
    price: int

class AuctionCreate(BaseModel):
    seller: str
    item: str
    base_price: int
    duration_minutes: int = Field(..., gt=0)

class BidIn(BaseModel):
    bidder: str
    item: str
    bid_amount: int

# Auth schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class UserRegister(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

# -------------------------
# App and middleware
# -------------------------
app = FastAPI(title="King Khufu Adventure Backend", version="3.0")

ALLOW_ORIGINS = [o.strip() for o in settings.allow_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# Rate limiting (Redis optional, else in-memory)
# -------------------------
RATE_LIMIT_WINDOW = settings.rate_limit_window
RATE_LIMIT_MAX = settings.rate_limit_max
_requests_log = defaultdict(list)

def is_rate_limited(ip: str) -> bool:
    if redis_client:
        key = f"rl:{ip}"
        try:
            val = redis_client.incr(key)
            if val == 1:
                redis_client.expire(key, RATE_LIMIT_WINDOW)
            return val > RATE_LIMIT_MAX
        except Exception:
            pass
    now = time.time()
    window = _requests_log[ip]
    while window and window[0] < now - RATE_LIMIT_WINDOW:
        window.pop(0)
    window.append(now)
    return len(window) > RATE_LIMIT_MAX

async def check_rate_limit(request: Request):
    ip = request.client.host if request.client else "unknown"
    if is_rate_limited(ip):
        raise HTTPException(status_code=429, detail="Too many requests")
    return

# -------------------------
# Leaderboard cache (Redis optional)
# -------------------------
_LEADERBOARD_CACHE: Dict[str, Any] = {"data": [], "ts": 0}
LEADERBOARD_TTL = settings.leaderboard_ttl

def get_cached_leaderboard(db: Session, limit: int = 10):
    now = time.time()
    if redis_client:
        try:
            raw = redis_client.get("leaderboard_cache")
            if raw:
                data = json.loads(raw)
                return data[:limit]
        except Exception:
            pass
    if now - _LEADERBOARD_CACHE["ts"] < LEADERBOARD_TTL and _LEADERBOARD_CACHE["data"]:
        return _LEADERBOARD_CACHE["data"][:limit]
    players = db.query(PlayerDB).order_by(PlayerDB.level.desc(), PlayerDB.coins.desc()).limit(limit).all()
    out = [{"username": p.username, "coins": p.coins, "level": p.level,
            "abilities": p.abilities, "avatar": p.avatar, "outfit": p.outfit,
            "achievements": p.achievements, "notifications": p.notifications} for p in players]
    _LEADERBOARD_CACHE["data"] = out
    _LEADERBOARD_CACHE["ts"] = now
    if redis_client:
        try:
            redis_client.setex("leaderboard_cache", int(LEADERBOARD_TTL), json.dumps(out))
        except Exception:
            pass
    return out

def invalidate_leaderboard_cache():
    _LEADERBOARD_CACHE["ts"] = 0
    _LEADERBOARD_CACHE["data"] = []
    if redis_client:
        try:
            redis_client.delete("leaderboard_cache")
        except Exception:
            pass

# -------------------------
# WebSocket manager (per-worker) + Redis Pub/Sub for multi-worker broadcast
# -------------------------
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("WebSocket connected: %s", websocket.client)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("WebSocket disconnected: %s", websocket.client)

    async def broadcast(self, message: Dict[str, Any]):
        to_remove = []
        for conn in list(self.active_connections):
            try:
                await conn.send_json(message)
            except Exception as e:
                logger.warning("WebSocket send failed: %s", e)
                to_remove.append(conn)
        for r in to_remove:
            self.disconnect(r)

manager = ConnectionManager()

# Redis Pub/Sub listener to forward messages to local WebSocket clients
async def redis_pubsub_listener():
    if not redis_client:
        return
    pubsub = redis_client.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe("leaderboard_channel")
    logger.info("Subscribed to Redis channel: leaderboard_channel")
    while True:
        try:
            message = pubsub.get_message(timeout=1.0)
            if message and message.get("data"):
                try:
                    payload = json.loads(message["data"])
                except Exception:
                    payload = {"type": "leaderboard_update", "data": message["data"]}
                await manager.broadcast(payload)
            await asyncio.sleep(0.01)
        except Exception as e:
            logger.exception("Redis pubsub listener error: %s", e)
            await asyncio.sleep(1)

# -------------------------
# Helpers and DB dependency
# -------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_player(db: Session, username: str) -> Optional[PlayerDB]:
    return db.query(PlayerDB).filter(PlayerDB.username == username).first()

def add_notification(db: Session, username: str, message: str):
    p = get_player(db, username)
    if p:
        notes = p.notifications or []
        notes.append({"message": message, "time": datetime.utcnow().isoformat()})
        p.notifications = notes
        db.add(p)
        db.commit()

def broadcast_leaderboard(db: Session):
    try:
        players = db.query(PlayerDB).order_by(PlayerDB.level.desc(), PlayerDB.coins.desc()).limit(10).all()
        payload = [{"username": p.username, "coins": p.coins, "level": p.level} for p in players]
        # local broadcast
        asyncio.create_task(manager.broadcast({"type": "leaderboard_update", "data": payload}))
        # update caches
        _LEADERBOARD_CACHE["data"] = payload
        _LEADERBOARD_CACHE["ts"] = time.time()
        if redis_client:
            try:
                redis_client.setex("leaderboard_cache", int(LEADERBOARD_TTL), json.dumps(payload))
                redis_client.publish("leaderboard_channel", json.dumps({"type": "leaderboard_update", "data": payload}))
            except Exception:
                pass
    except Exception as e:
        logger.exception("broadcast_leaderboard failed: %s", e)

# -------------------------
# Rate-limit dependency wrapper
# -------------------------
async def rate_limit_dependency(request: Request):
    return await check_rate_limit(request)

# -------------------------
# Prices (preserve original)
# -------------------------
PRICES = {
    "double_jump": 5,
    "shield": 7,
    "magic": 10,
    "strength": 12,
    "speed": 15,
    "camel": 20,
    "fast_mode": 25,
    "pharaonic_outfit": 15,
    "avatar_warrior": 10
}

# -------------------------
# Auth utilities (bcrypt + JWT)
# -------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_failed_attempts_redis_prefix = "failed_attempts:"  # if redis used

def verify_password(plain_password, hashed_password):
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(subject: str, expires_delta: Optional[timedelta] = None):
    to_encode = {"sub": subject}
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        return None

def get_username_from_auth_header(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    try:
        parts = authorization.split()
        if len(parts) != 2:
            return None
        scheme, token = parts
        if scheme.lower() != "bearer":
            return None
        payload = decode_access_token(token)
        if not payload:
            return None
        return payload.get("sub")
    except Exception:
        return None

# failed attempts handling (Redis-backed if available)
def increment_failed_attempts(username: str):
    if redis_client:
        key = f"{_failed_attempts_redis_prefix}{username}"
        try:
            val = redis_client.incr(key)
            if val == 1:
                redis_client.expire(key, settings.account_lock_seconds)
            return int(val)
        except Exception:
            pass
    fa = _failed_attempts[username]
    fa["count"] += 1
    if not fa["first_failed_at"]:
        fa["first_failed_at"] = datetime.utcnow().timestamp()
    return fa["count"]

def reset_failed_attempts(username: str):
    if redis_client:
        try:
            redis_client.delete(f"{_failed_attempts_redis_prefix}{username}")
            return
        except Exception:
            pass
    _failed_attempts[username] = {"count": 0, "first_failed_at": None, "locked_until": None}

def is_account_locked(username: str) -> bool:
    if redis_client:
        try:
            key = f"{_failed_attempts_redis_prefix}{username}"
            val = redis_client.get(key)
            if val and int(val) >= settings.account_lock_threshold:
                return True
            return False
        except Exception:
            pass
    fa = _failed_attempts[username]
    if fa["locked_until"] and datetime.utcnow().timestamp() < fa["locked_until"]:
        return True
    return False

# -------------------------
# Endpoints (preserve original behavior, add auth & improvements)
# -------------------------

@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}

@app.get("/metrics")
def metrics(db: Session = Depends(get_db)):
    players_count = db.query(func.count(PlayerDB.id)).scalar()
    auctions_count = db.query(func.count(AuctionDB.id)).scalar()
    market_count = db.query(func.count(MarketItemDB.id)).scalar()
    return {"players": players_count, "auctions": auctions_count, "market_items": market_count}

# Auth endpoints (non-destructive)
@app.post("/auth/register", response_model=Token, dependencies=[Depends(rate_limit_dependency)])
def register(user: UserRegister, db: Session = Depends(get_db)):
    existing = get_player(db, user.username)
    if existing:
        raise HTTPException(status_code=400, detail="اسم المستخدم موجود بالفعل")
    hashed = get_password_hash(user.password)
    new_p = PlayerDB(username=user.username, hashed_password=hashed, coins=0, level=1)
    db.add(new_p)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="فشل إنشاء المستخدم")
    db.refresh(new_p)
    access_token = create_access_token(new_p.username)
    logger.info("User registered: %s", new_p.username)
    invalidate_leaderboard_cache()
    broadcast_leaderboard(db)
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/auth/login", response_model=Token, dependencies=[Depends(rate_limit_dependency)])
def login(user: UserLogin, db: Session = Depends(get_db)):
    if is_account_locked(user.username):
        raise HTTPException(status_code=403, detail="الحساب مقفل مؤقتًا بسبب محاولات فاشلة. حاول لاحقًا.")
    p = get_player(db, user.username)
    if not p or not p.hashed_password:
        count = increment_failed_attempts(user.username)
        if count >= settings.account_lock_threshold:
            # set lock in memory if no redis
            _failed_attempts[user.username]["locked_until"] = datetime.utcnow().timestamp() + settings.account_lock_seconds
        raise HTTPException(status_code=400, detail="اسم المستخدم أو كلمة المرور غير صحيحة")
    if not verify_password(user.password, p.hashed_password):
        count = increment_failed_attempts(user.username)
        if count >= settings.account_lock_threshold:
            _failed_attempts[user.username]["locked_until"] = datetime.utcnow().timestamp() + settings.account_lock_seconds
        raise HTTPException(status_code=400, detail="اسم المستخدم أو كلمة المرور غير صحيحة")
    reset_failed_attempts(user.username)
    access_token = create_access_token(p.username)
    logger.info("User logged in: %s", p.username)
    return {"access_token": access_token, "token_type": "bearer"}

def effective_username(request: Request, provided_username: Optional[str]) -> Optional[str]:
    auth_header = request.headers.get("authorization")
    token_user = get_username_from_auth_header(auth_header)
    if token_user:
        return token_user
    return provided_username

@app.post("/pay", dependencies=[Depends(rate_limit_dependency)])
def pay(request: PaymentRequest, db: Session = Depends(get_db)):
    if request.amount < 3.0:
        raise HTTPException(status_code=400, detail="المبلغ غير كافي للاشتراك")
    expiry_date = (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d")
    logger.info("Payment: phone=%s amount=%s", request.phone_number, request.amount)
    return {"status": "success", "details": {"phone_number": request.phone_number, "amount": request.amount, "expiry": expiry_date}}

@app.post("/players", response_model=PlayerOut, dependencies=[Depends(rate_limit_dependency)])
def create_or_update_player(player: PlayerCreate, db: Session = Depends(get_db)):
    existing = get_player(db, player.username)
    if existing:
        existing.coins = player.coins
        existing.level = player.level
        existing.abilities = player.abilities
        existing.avatar = player.avatar
        existing.outfit = player.outfit
        existing.achievements = player.achievements
        existing.notifications = player.notifications
        if player.password:
            existing.hashed_password = get_password_hash(player.password)
        db.add(existing)
        db.commit()
        db.refresh(existing)
        logger.info("Updated player %s", player.username)
        invalidate_leaderboard_cache()
        broadcast_leaderboard(db)
        return PlayerOut(**existing.__dict__)
    else:
        new_p = PlayerDB(
            username=player.username,
            coins=player.coins,
            level=player.level,
            abilities=player.abilities,
            avatar=player.avatar,
            outfit=player.outfit,
            achievements=player.achievements,
            notifications=player.notifications,
            hashed_password=get_password_hash(player.password) if player.password else None
        )
        db.add(new_p)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=400, detail="اسم المستخدم موجود بالفعل")
        db.refresh(new_p)
        logger.info("Created player %s", player.username)
        invalidate_leaderboard_cache()
        broadcast_leaderboard(db)
        return PlayerOut(**new_p.__dict__)

@app.get("/leaderboard", response_model=List[PlayerOut], dependencies=[Depends(rate_limit_dependency)])
def get_leaderboard(limit: int = Query(10, ge=1, le=100), db: Session = Depends(get_db)):
    out = get_cached_leaderboard(db, limit)
    return [PlayerOut(**p) for p in out]

@app.get("/players/{username}", response_model=PlayerOut, dependencies=[Depends(rate_limit_dependency)])
def get_player_info(username: str, db: Session = Depends(get_db)):
    p = get_player(db, username)
    if not p:
        raise HTTPException(status_code=404, detail="لاعب غير موجود")
    return PlayerOut(**p.__dict__)

@app.post("/shop/buy", dependencies=[Depends(rate_limit_dependency)])
def buy_item(request: Request, username: str = None, item: str = None, db: Session = Depends(get_db)):
    eff_username = effective_username(request, username)
    if not eff_username:
        raise HTTPException(status_code=400, detail="اسم المستخدم مطلوب")
    if item is None:
        raise HTTPException(status_code=400, detail="اسم العنصر مطلوب")
    price = PRICES.get(item)
    if price is None:
        raise HTTPException(status_code=400, detail="عنصر غير موجود")
    try:
        with db.begin():
            player = db.query(PlayerDB).filter(PlayerDB.username == eff_username).with_for_update().first()
            if not player:
                raise HTTPException(status_code=404, detail="لاعب غير موجود")
            if player.coins < price:
                return {"status": "failed", "reason": "رصيد غير كافي"}
            player.coins -= price
            abilities = player.abilities or {}
            abilities[item] = True
            player.abilities = abilities
            achs = player.achievements or []
            achievement = f"اشترى {item}"
            if achievement not in achs:
                achs.append(achievement)
                player.achievements = achs
                add_notification(db, eff_username, f"إنجاز جديد: {achievement}")
            db.add(player)
        db.refresh(player)
        invalidate_leaderboard_cache()
        broadcast_leaderboard(db)
        return {"status": "success", "item": item, "remaining_coins": player.coins}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("buy_item failed: %s", e)
        raise HTTPException(status_code=500, detail="خطأ في الخادم")

@app.get("/daily_challenge", dependencies=[Depends(rate_limit_dependency)])
def daily_challenge():
    challenges = [
        "اجمع 50 عملة في مستوى واحد",
        "اهزم 10 أعداء بدون خسارة",
        "أكمل 3 مستويات متتالية بدون توقف",
        "اشتري جمل واستخدمه في الصحراء",
        "غيّر ملابسك إلى زي فرعوني",
        "اشترِ قوة إضافية واهزم زعيم المستوى"
    ]
    idx = datetime.utcnow().day % len(challenges)
    return {"challenge": challenges[idx]}

@app.get("/achievements/{username}", dependencies=[Depends(rate_limit_dependency)])
def get_achievements(username: str, db: Session = Depends(get_db)):
    p = get_player(db, username)
    if not p:
        raise HTTPException(status_code=404, detail="لاعب غير موجود")
    return {"achievements": p.achievements or []}

@app.get("/notifications/{username}", dependencies=[Depends(rate_limit_dependency)])
def get_notifications(username: str, db: Session = Depends(get_db)):
    p = get_player(db, username)
    if not p:
        raise HTTPException(status_code=404, detail="لاعب غير موجود")
    return {"notifications": p.notifications or []}

@app.post("/marketplace/sell", dependencies=[Depends(rate_limit_dependency)])
def sell_item(request: Request, payload: MarketItemIn = None, db: Session = Depends(get_db)):
    eff_seller = effective_username(request, payload.seller if payload else None)
    if not eff_seller:
        raise HTTPException(status_code=400, detail="اسم البائع مطلوب")
    item = MarketItemDB(seller=eff_seller, item=payload.item, price=payload.price)
    db.add(item)
    db.commit()
    players = db.query(PlayerDB).all()
    for p in players:
        add_notification(db, p.username, f"عنصر جديد في السوق: {payload.item} بسعر {payload.price} من {eff_seller}")
    return {"status": "success", "item": payload.item, "price": payload.price}

@app.get("/marketplace", dependencies=[Depends(rate_limit_dependency)])
def view_marketplace(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    items = db.query(MarketItemDB).filter(MarketItemDB.is_sold == False).order_by(MarketItemDB.created_at.desc()).offset(skip).limit(limit).all()
    return {"items": [{"id": i.id, "seller": i.seller, "item": i.item, "price": i.price} for i in items]}

@app.post("/marketplace/buy", dependencies=[Depends(rate_limit_dependency)])
def buy_from_market(request: Request, buyer: str = None, item_id: int = None, db: Session = Depends(get_db)):
    eff_buyer = effective_username(request, buyer)
    if not eff_buyer:
        raise HTTPException(status_code=400, detail="اسم المشتري مطلوب")
    try:
        with db.begin():
            player = db.query(PlayerDB).filter(PlayerDB.username == eff_buyer).with_for_update().first()
            if not player:
                raise HTTPException(status_code=404, detail="لاعب غير موجود")
            market_item = db.query(MarketItemDB).filter(MarketItemDB.id == item_id, MarketItemDB.is_sold == False).with_for_update().first()
            if not market_item:
                raise HTTPException(status_code=404, detail="العنصر غير موجود في السوق")
            if player.coins < market_item.price:
                return {"status": "failed", "reason": "رصيد غير كافي"}
            player.coins -= market_item.price
            abilities = player.abilities or {}
            abilities[market_item.item] = True
            player.abilities = abilities
            # soft-delete: mark sold and set buyer
            market_item.is_sold = True
            market_item.buyer = eff_buyer
            achs = player.achievements or []
            achievement = f"اشترى {market_item.item} من السوق"
            if achievement not in achs:
                achs.append(achievement)
                player.achievements = achs
                add_notification(db, eff_buyer, f"إنجاز جديد: {achievement}")
            db.add(player)
            db.add(market_item)
        db.refresh(player)
        invalidate_leaderboard_cache()
        broadcast_leaderboard(db)
        return {"status": "success", "item": market_item.item, "remaining_coins": player.coins}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("buy_from_market failed: %s", e)
        raise HTTPException(status_code=500, detail="خطأ في الخادم")

# -------------------------
# Auctions with escrow system and async worker
# -------------------------
@app.post("/auction/create", dependencies=[Depends(rate_limit_dependency)])
def create_auction(request: Request, payload: AuctionCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    eff_seller = effective_username(request, payload.seller)
    if not eff_seller:
        raise HTTPException(status_code=400, detail="اسم البائع مطلوب")
    end_time = datetime.utcnow() + timedelta(minutes=payload.duration_minutes)
    auction = AuctionDB(
        seller=eff_seller,
        item=payload.item,
        base_price=payload.base_price,
        highest_bid=payload.base_price,
        highest_bidder=None,
        end_time=end_time,
        closed=False
    )
    db.add(auction)
    db.commit()
    db.refresh(auction)
    # schedule via background worker (worker scans DB periodically)
    players = db.query(PlayerDB).all()
    for p in players:
        add_notification(db, p.username, f"مزاد جديد على {payload.item} بسعر ابتدائي {payload.base_price}")
    return {"status": "success", "auction_id": auction.id, "end_time": auction.end_time.isoformat()}

@app.post("/auction/bid", dependencies=[Depends(rate_limit_dependency)])
def place_bid(bid: BidIn, db: Session = Depends(get_db)):
    # Escrow logic: deduct bid amount immediately, refund previous highest bidder
    try:
        with db.begin():
            player = db.query(PlayerDB).filter(PlayerDB.username == bid.bidder).with_for_update().first()
            if not player:
                raise HTTPException(status_code=404, detail="لاعب غير موجود")
            auction = db.query(AuctionDB).filter(AuctionDB.item == bid.item, AuctionDB.closed == False).with_for_update().first()
            if not auction:
                raise HTTPException(status_code=404, detail="المزاد غير موجود أو مغلق")
            if datetime.utcnow() > auction.end_time:
                auction.closed = True
                db.add(auction)
                raise HTTPException(status_code=400, detail="المزاد انتهى")
            if bid.bid_amount <= auction.highest_bid:
                raise HTTPException(status_code=400, detail="العرض أقل من أو يساوي أعلى مزايدة حالية")
            if player.coins < bid.bid_amount:
                raise HTTPException(status_code=400, detail="رصيد غير كافي للمزايدة")
            # Deduct new bid from bidder immediately (escrow)
            player.coins -= bid.bid_amount
            db.add(player)
            # Refund previous highest bidder if exists
            prev_bidder = auction.highest_bidder
            prev_amount = auction.highest_bid
            if prev_bidder:
                prev = db.query(PlayerDB).filter(PlayerDB.username == prev_bidder).with_for_update().first()
                if prev:
                    prev.coins += prev_amount
                    db.add(prev)
            # Update auction highest bid info
            auction.highest_bid = bid.bid_amount
            auction.highest_bidder = bid.bidder
            db.add(auction)
        # outside transaction: notify seller
        add_notification(db, auction.seller, f"تمت مزايدة على {auction.item} من {bid.bidder} بمبلغ {bid.bid_amount}")
        invalidate_leaderboard_cache()
        broadcast_leaderboard(db)
        return {"status": "success", "highest_bid": auction.highest_bid, "highest_bidder": auction.highest_bidder}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("place_bid failed: %s", e)
        raise HTTPException(status_code=500, detail="خطأ في الخادم")

@app.get("/auctions", dependencies=[Depends(rate_limit_dependency)])
def list_auctions(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    auctions = db.query(AuctionDB).order_by(AuctionDB.end_time.asc()).offset(skip).limit(limit).all()
    return {"auctions": [
        {
            "id": a.id,
            "seller": a.seller,
            "item": a.item,
            "base_price": a.base_price,
            "highest_bid": a.highest_bid,
            "highest_bidder": a.highest_bidder,
            "end_time": a.end_time.isoformat(),
            "closed": a.closed
        } for a in auctions
    ]}

def close_auction_logic(db: Session, auction: AuctionDB):
    """
    Close auction and finalize escrow:
    - If highest_bidder exists, transfer item ownership (mark in DB via notifications/abilities).
    - Do NOT deduct again (already escrowed). Just confirm transfer.
    - Refund nothing here because previous refunds were done at bid time.
    """
    try:
        if auction.closed:
            return
        auction.closed = True
        db.add(auction)
        db.commit()
        if auction.highest_bidder:
            winner = get_player(db, auction.highest_bidder)
            if winner:
                abilities = winner.abilities or {}
                abilities[auction.item] = True
                winner.abilities = abilities
                db.add(winner)
                db.commit()
                add_notification(db, winner.username, f"فزت بالمزاد على {auction.item} بمبلغ {auction.highest_bid}")
                add_notification(db, auction.seller, f"تم بيع {auction.item} إلى {winner.username} بمبلغ {auction.highest_bid}")
        invalidate_leaderboard_cache()
        broadcast_leaderboard(db)
        logger.info("Auction %s closed (finalized)", auction.id)
    except Exception as e:
        logger.exception("Error finalizing auction %s: %s", auction.id, e)

async def auction_closing_worker():
    """
    Periodic async worker that scans for auctions to close.
    This is resilient to server restarts (worker restarts and picks up pending auctions).
    """
    await asyncio.sleep(1)  # small startup delay
    while True:
        try:
            db = SessionLocal()
            now = datetime.utcnow()
            auctions_to_close = db.query(AuctionDB).filter(AuctionDB.end_time <= now, AuctionDB.closed == False).all()
            for a in auctions_to_close:
                logger.info("Closing auction id=%s item=%s", a.id, a.item)
                close_auction_logic(db, a)
            db.close()
        except Exception as e:
            logger.exception("auction_closing_worker error: %s", e)
        await asyncio.sleep(settings.auction_worker_interval_seconds)

# -------------------------
# WebSocket endpoint
# -------------------------
@app.websocket("/ws/leaderboard")
async def websocket_leaderboard(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        db = SessionLocal()
        players = db.query(PlayerDB).order_by(PlayerDB.level.desc(), PlayerDB.coins.desc()).limit(10).all()
        payload = [{"username": p.username, "coins": p.coins, "level": p.level} for p in players]
        await websocket.send_json({"type": "leaderboard_init", "data": payload})
        db.close()
        while True:
            msg = await websocket.receive_text()
            await websocket.send_json({"type": "pong", "message": msg})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.exception("WebSocket error: %s", e)
        manager.disconnect(websocket)

# -------------------------
# Startup tasks
# -------------------------
@app.on_event("startup")
async def on_startup():
    logger.info("Starting King Khufu Backend")
    # warm leaderboard cache
    try:
        db = SessionLocal()
        get_cached_leaderboard(db, limit=10)
        db.close()
    except Exception:
        logger.exception("Failed to warm leaderboard cache")
    # start Redis pubsub listener if redis available
    if redis_client:
        asyncio.create_task(redis_pubsub_listener())
    # start auction closing worker
    asyncio.create_task(auction_closing_worker())

# -------------------------
# Run (uvicorn recommended)
# -------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)
