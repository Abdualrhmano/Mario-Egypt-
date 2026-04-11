from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict
from datetime import datetime, timedelta

app = FastAPI(title="King Khufu Adventure Backend", version="9.0")

# ===== نماذج البيانات =====
class PaymentRequest(BaseModel):
    phone_number: str
    amount: float

class Player(BaseModel):
    username: str
    coins: int = 0
    level: int = 1
    abilities: Dict[str, bool] = {}
    avatar: str = "default"
    outfit: str = "basic"
    achievements: List[str] = []
    notifications: List[str] = []

class MarketItem(BaseModel):
    seller: str
    item: str
    price: int

class AuctionItem(BaseModel):
    seller: str
    item: str
    base_price: int
    highest_bid: int = 0
    highest_bidder: str = None
    end_time: datetime

# ===== قاعدة بيانات مؤقتة =====
leaderboard: List[Player] = []
marketplace: List[MarketItem] = []
auctions: List[AuctionItem] = []

# ===== API للدفع والاشتراك =====
@app.post("/pay")
def pay(request: PaymentRequest):
    if request.amount < 3.0:
        raise HTTPException(status_code=400, detail="المبلغ غير كافي للاشتراك")
    expiry_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    return {
        "status": "success",
        "details": {
            "phone_number": request.phone_number,
            "amount": request.amount,
            "expiry": expiry_date
        }
    }

# ===== API للمتصدرين =====
@app.post("/leaderboard")
def update_leaderboard(player: Player):
    existing = next((p for p in leaderboard if p.username == player.username), None)
    if existing:
        existing.coins = player.coins
        existing.level = player.level
        existing.abilities = player.abilities
        existing.avatar = player.avatar
        existing.outfit = player.outfit
        existing.achievements = player.achievements
        existing.notifications = player.notifications
    else:
        leaderboard.append(player)
    leaderboard.sort(key=lambda p: (p.level, p.coins), reverse=True)
    return {"status": "updated"}

@app.get("/leaderboard")
def get_leaderboard():
    top_players = leaderboard[:10]
    return {"top_players": [p.dict() for p in top_players]}

# ===== API للمتجر =====
@app.post("/shop/buy")
def buy_item(username: str, item: str):
    player = next((p for p in leaderboard if p.username == username), None)
    if not player:
        raise HTTPException(status_code=404, detail="لاعب غير موجود")

    prices = {
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

    if item not in prices:
        raise HTTPException(status_code=400, detail="عنصر غير موجود")

    if player.coins >= prices[item]:
        player.coins -= prices[item]
        player.abilities[item] = True
        achievement = f"اشترى {item}"
        if achievement not in player.achievements:
            player.achievements.append(achievement)
            add_notification(username, f"إنجاز جديد: {achievement}")
        return {"status": "success", "item": item, "remaining_coins": player.coins}
    else:
        return {"status": "failed", "reason": "رصيد غير كافي"}

# ===== API للتحديات اليومية =====
@app.get("/daily_challenge")
def daily_challenge():
    challenges = [
        "اجمع 50 عملة في مستوى واحد",
        "اهزم 10 أعداء بدون خسارة",
        "أكمل 3 مستويات متتالية بدون توقف",
        "اشتري جمل واستخدمه في الصحراء",
        "غيّر ملابسك إلى زي فرعوني",
        "اشترِ قوة إضافية واهزم زعيم المستوى"
    ]
    today_index = datetime.now().day % len(challenges)
    return {"challenge": challenges[today_index]}

# ===== API للإنجازات =====
@app.get("/achievements/{username}")
def get_achievements(username: str):
    player = next((p for p in leaderboard if p.username == username), None)
    if not player:
        raise HTTPException(status_code=404, detail="لاعب غير موجود")
    return {"achievements": player.achievements}

# ===== API للسوق (Marketplace) =====
@app.post("/marketplace/sell")
def sell_item(seller: str, item: str, price: int):
    market_item = MarketItem(seller=seller, item=item, price=price)
    marketplace.append(market_item)
    for p in leaderboard:
        add_notification(p.username, f"عنصر جديد في السوق: {item} بسعر {price} من {seller}")
    return {"status": "success", "item": item, "price": price}

@app.post("/marketplace/buy")
def buy_from_market(buyer: str, item: str):
    player = next((p for p in leaderboard if p.username == buyer), None)
    if not player:
        raise HTTPException(status_code=404, detail="لاعب غير موجود")

    market_item = next((m for m in marketplace if m.item == item), None)
    if not market_item:
        raise HTTPException(status_code=404, detail="العنصر غير موجود في السوق")

    if player.coins >= market_item.price:
        player.coins -= market_item.price
        player.abilities[item] = True
        marketplace.remove(market_item)
        achievement = f"اشترى {item} من السوق"
        if achievement not in player.achievements:
            player.achievements.append(achievement)
            add_notification(buyer, f"إنجاز جديد: {achievement}")
        return {"status": "success", "item": item, "remaining_coins": player.coins}
    else:
        return {"status": "failed", "reason": "رصيد غير كافي"}

@app.get("/marketplace")
def view_marketplace():
    return {"items": [m.dict() for m in marketplace]}

# ===== API للمزادات (Auction System) =====
@app.post("/auction/create")
def create_auction(seller: str, item: str, base_price: int, duration_minutes: int):
    end_time = datetime.now() + timedelta(minutes=duration_minutes)
    auction = AuctionItem(
        seller=seller,
        item=item,
        base_price=base_price,
        highest_bid=base_price,
        highest_bidder=None,
        end_time=end_time
    )
    auctions.append(auction)
    for p in leaderboard:
        add_notification(p.username, f"مزاد جديد على {item} بسعر ابتدائي {base_price}")
    return {"status": "success", "auction": auction.dict()}

@app.post("/auction/bid")
def place_bid(bidder: str, item: str, bid_amount: int):
    player = next((p for p in leaderboard if p.username == bidder), None)
    if not player:
        raise HTTPException(status_code=404, detail="لاعب غير موجود")

    auction = next((a for a in auctions if a.item == item), None)
    if not auction:
        raise HTTPException(status_code=404, detail="المزاد غير موجود")

    if datetime.now() > auction.end_time:
        raise HTTPException(status_code=400, detail="المزاد انتهى")

    if bid_amount <= auction.highest_bid:
        raise HTTPException(status_code=400, detail="العرض أقل من أو يساوي أعلى مزايدة حالية")

    if player.coins < bid_amount:
        raise HTTPException(status_code=400, detail="رصيد غير كافي للمزايدة")

    auction.highest_bid = bid_amount
    auction.highest_bidder = bidder
    return {"status": "success", "highest_bid": auction.highest_bid, "highest_bidder": auction.highest_bidder}

@app.post("/auction/close")
def close_auction(item: str):
    auction = next((a for a in auctions if a.item == item), None)
    if not auction:
        raise HTTPException(status_code=404, detail="المزاد غير موجود")

    if datetime.now() < auction.end_time:
        raise HTTPException(status_code=400, detail="المزاد لم ينته بعد")

    if auction.highest_bidder:
        buyer = next((p for p in leaderboard if p.username == auction.highest_bidder), None)
        seller = next((p for p in leaderboard if p.username == auction.seller), None)
