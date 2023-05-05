import asyncio
import os
import sqlite3
import threading
from collections import namedtuple
from datetime import datetime
from typing import Optional

import aiohttp
import pytz

LAST_QUERY_TIME = None
LAST_QUERY_TIME_LOCK = threading.Lock()
TIMEZONE_TAIWAN = pytz.timezone("Asia/Taipei")
MINIMUM_EARNING_RATE_REQUIREMENT = 5.0
SHORT_MONEY_LOCK_DAYS = 31
DATA_GIFT = namedtuple("Gift", [
    "id",
    "name",
    "description",
    "price",
    "earning_rate",
    "money_lock_days",
    "gift_ended_time",
    "gift_expiration_time",
    "period_days",
    "period_type",
    "max_point_earning",
    "earning_delay_days"
])


class Gift:
    def __init__(
        self,
        id: int,
        name: str,
        price: int,
        period_type: str,
        gift_ended_time: str,
        earning_rate: float,
        earning_delay_days: int,
        voucher_type: str,
        period_days: Optional[int] = None,
        gift_expiration_time: Optional[str] = None,
        max_point_earning: Optional[float] = None,
        gift_expiration_timestamp: Optional[datetime] = None,
        money_lock_days: Optional[int] = None,
    ):
        self.id = id
        self.name = name
        self.price = price
        self.period_type = period_type
        self.gift_ended_time = gift_ended_time
        self.earning_rate = earning_rate
        self.earning_delay_days = earning_delay_days
        self.voucher_type = voucher_type
        self.period_days = period_days
        self.gift_expiration_time = gift_expiration_time
        self.max_point_earning = max_point_earning
        self.gift_expiration_timestamp = gift_expiration_timestamp
        self.money_lock_days = money_lock_days

    @classmethod
    def from_dict(cls, data: dict):
        point_earning_policy = data.get("pointEarningPolicy", {})
        detail_product = data.get("detailProduct", {})
        ecoupon = detail_product.get("ecoupon", {})

        gift_ended_timestamp = datetime.fromtimestamp(point_earning_policy.get("endedTimestamp") // 1000)
        gift_ended_time = gift_ended_timestamp.astimezone(TIMEZONE_TAIWAN).strftime("%Y-%m-%d %H:%M:%S")
        
        gift_expiration_timestamp = (
            datetime.fromtimestamp(ecoupon.get("validEndTimestamp") // 1000)
            if ecoupon.get("validEndTimestamp", None)
            else None
        )
        gift_expiration_time = (
            gift_expiration_timestamp.astimezone(TIMEZONE_TAIWAN).strftime("%Y-%m-%d %H:%M:%S")
            if gift_expiration_timestamp
            else None
        )
        period_days=ecoupon.get("periodDays")
        if period_days:
            money_lock_days = period_days
        elif gift_expiration_timestamp:
            time_diff = gift_expiration_timestamp - gift_ended_timestamp
            money_lock_days = time_diff.days

        return cls(
            id=detail_product.get("id"),
            name=detail_product.get("name"),
            price=detail_product.get("discountedPrice"),
            period_type=ecoupon.get("periodType"),
            gift_ended_time=gift_ended_time,
            earning_rate=point_earning_policy.get("earningRate"),
            earning_delay_days=point_earning_policy.get("earningDelay"),
            voucher_type=ecoupon.get("voucherType"),
            period_days=period_days,
            gift_expiration_time=gift_expiration_time,
            max_point_earning=point_earning_policy.get("maxPointEarning"),
            gift_expiration_timestamp=gift_expiration_timestamp,
            money_lock_days=money_lock_days,
        )


async def list_category_ids(session):
    url = f"https://giftshop-tw.line.me/api/category/v3"
    async with session.get(url) as response:
        if response.status == 200:
            data = dict(await response.json())
            return [dict(category).get("categoryId") for category in data.get("result", {}).get("voucherCategories", [])]
        else:
            print(f"無法取得 categorire")
            return []


async def list_category_gift_ids(session, category_id, page=1, results=[]):
    url = f"https://giftshop-tw.line.me/api/category/v2/{category_id}/products/more?sortType=PRICE_DESC&periodTypes=FIXED&periodTypes=FLEXIBLE&voucherTypes=ONE_TIME&payType=NORMAL&page={page}"
    async with session.get(url) as response:
        if response.status == 200:
            data = await response.json()
            content = data["result"]["content"]
            for gift in content:
                if gift["pointEarningPolicy"] is not None:
                    results.append(gift["id"])
            
            if not data["result"]["last"]:
                await asyncio.sleep(0.01)
                results = await list_category_gift_ids(session, category_id, page + 1, results)
                
        return results


async def fetch_gift(session, gift_id):
    url = f"https://giftshop-tw.line.me/api/products/v3/{gift_id}"
    retry_count = 0
    while retry_count < 3:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
            else:
                retry_count += 1
                await asyncio.sleep(0.02)
    return None


async def crawl_line_gifts(conn, cursor):
    global LAST_QUERY_TIME
    with LAST_QUERY_TIME_LOCK:
        now = datetime.now()
        # cache for 1 hour
        if LAST_QUERY_TIME is None or (now - LAST_QUERY_TIME).total_seconds() > 3600:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS gifts (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    price INTEGER,
                    earning_rate REAL,
                    money_lock_days INTEGER,
                    gift_ended_time TEXT,
                    gift_expiration_time TEXT,
                    period_days INTEGER,
                    period_type TEXT,
                    max_point_earning REAL,
                    earning_delay_days INTEGER
                )
                """
            )
            
            async with aiohttp.ClientSession() as session:
                category_ids = await list_category_ids(session)
                print(f"取得 {len(category_ids)} 個 category")

                for category_id in category_ids:
                    category_gift_ids = await list_category_gift_ids(session, category_id)
                    print(f"category {category_id} 取得 {len(category_gift_ids)} 個 gift")

                    tasks = []
                    for category_gift_id in category_gift_ids:
                        task = asyncio.create_task(fetch_gift(session, category_gift_id))
                        tasks.append(task)
                        
                    responses = await asyncio.gather(*tasks)
                    for response in responses:
                        gift = Gift.from_dict(response.get("result"))
                        gift_description = (
                            f"{gift.earning_rate}%, ${gift.price}, 銷售至 {gift.gift_ended_time}, "
                        )

                        if gift.period_days:
                            gift_description = f"{gift_description}可兌換至銷售後 {gift.period_days} 天\n"
                        elif gift.gift_expiration_time:
                            gift_description = f"{gift_description}可兌換至 {gift.gift_expiration_time}\n"

                        gift_description = (
                            f"{gift_description}最後一天買的話，錢錢被卡 {gift.money_lock_days} 天, {gift.earning_delay_days}天後給點\n"
                            f"{gift.name}\n"
                            f"https://giftshop-tw.line.me/voucher/{gift.id}"
                        )

                        cursor.execute(
                            """
                            INSERT INTO gifts 
                            (id, name, description, price, earning_rate, money_lock_days, gift_ended_time, gift_expiration_time, period_days, period_type, max_point_earning, earning_delay_days)
                            VALUES
                            (:id, :name, :description, :price, :earning_rate, :money_lock_days, :gift_ended_time, :gift_expiration_time, :period_days, :period_type, :max_point_earning, :earning_delay_days)
                            ON CONFLICT(id) DO UPDATE SET
                            name = :name,
                            description = :description,
                            price = :price,
                            earning_rate = :earning_rate,
                            money_lock_days = :money_lock_days,
                            gift_ended_time = :gift_ended_time,
                            gift_expiration_time = :gift_expiration_time,
                            period_days = :period_days,
                            period_type = :period_type,
                            max_point_earning = :max_point_earning,
                            earning_delay_days = :earning_delay_days
                            """,
                            {
                                "id": gift.id,
                                "name": gift.name,
                                "description": gift_description,
                                "price": gift.price,
                                "earning_rate": gift.earning_rate,
                                "money_lock_days": gift.money_lock_days,
                                "gift_ended_time": gift.gift_ended_time,
                                "gift_expiration_time": gift.gift_expiration_time,
                                "period_days": gift.period_days,
                                "period_type": gift.period_type,
                                "max_point_earning": gift.max_point_earning,
                                "earning_delay_days": gift.earning_delay_days,
                            },
                        )
                        conn.commit()
                        print(gift_description)
                        print("------------------------------------")

async def get_answer(rate=MINIMUM_EARNING_RATE_REQUIREMENT, days=SHORT_MONEY_LOCK_DAYS):
    def float_or_none(string):
        try:
            return float(string)
        except ValueError:
            return False
    
    rate = float_or_none(rate) or MINIMUM_EARNING_RATE_REQUIREMENT
    days = int(days) if days.isdigit() else SHORT_MONEY_LOCK_DAYS

    if not os.path.isfile("line_gift.db"):
        return None
        
    conn = sqlite3.connect("line_gift.db")
    cursor = conn.cursor()
    
    # refresh db data
    await crawl_line_gifts(conn, cursor)
    
    results = cursor.execute(
        """
        SELECT * FROM gifts
        WHERE earning_rate <= :rate AND 1 <= money_lock_days AND money_lock_days < :days
        ORDER BY money_lock_days DESC, earning_rate ASC
        LIMIT 10;
        """,
        {
            "rate": rate,
            "days": days,
        },
    ).fetchall()

    if len(results) > 0:
        gifts = [DATA_GIFT(*row) for row in results]
        return "\n".join([
            f"{gift.earning_rate}%, {gift.price}, 卡 {gift.money_lock_days} 天, [🔗](https://giftshop-tw.line.me/voucher/{gift.id})" 
            for gift in gifts
        ])
    else:
        return "窩不知道"
