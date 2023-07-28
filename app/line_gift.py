import asyncio
import logging
import os
from datetime import datetime
from typing import Optional

import aiohttp
import pytz
from cachetools import TTLCache
from telegram.constants import ParseMode

LOG_LEVEL = os.getenv("LOG_LEVEL", default="INFO")
TIMEZONE_TAIWAN = pytz.timezone("Asia/Taipei")
SHORT_MONEY_LOCK_DAYS = 50

CACHE = TTLCache(maxsize=100, ttl=21600)  # 21600 = 6 hours

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=LOG_LEVEL)
logger = logging.getLogger(__name__)


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
        period_days = ecoupon.get("periodDays")
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
            logger.info(f"無法取得 categorire")
            return []


async def list_category_gift_ids(session, category_id, target_rate, page=1, results=[]):
    url = f"https://giftshop-tw.line.me/api/category/v2/{category_id}/products/more?sortType=PRICE_DESC&periodTypes=FIXED&periodTypes=FLEXIBLE&voucherTypes=ONE_TIME&payType=NORMAL&page={page}"

    async with session.get(url) as response:
        if response.status == 200:
            data = await response.json()
            content = data["result"]["content"]
            for gift in content:
                if gift["pointEarningPolicy"] is not None:
                    if gift["pointEarningPolicy"]["earningRate"] >= target_rate:
                        results.append(gift["id"])

            if not data["result"]["last"]:
                await asyncio.sleep(0.1)
                results = await list_category_gift_ids(session, category_id, target_rate, page + 1, results)

        return results


async def fetch_gift(session, gift_id):
    url = f"https://giftshop-tw.line.me/api/products/v3/{gift_id}"
    retry_count = 0
    while retry_count < 5:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    retry_count += 1
                    await asyncio.sleep(0.05)
        except:
            retry_count += 1
            await asyncio.sleep(0.05)
    return None


async def crawl_line_gifts(target_rate: float, bot, reply_msg):
    if target_rate in CACHE:
        await bot.edit_message_text(
            chat_id=reply_msg.chat_id, message_id=reply_msg.message_id, text=CACHE[target_rate], parse_mode=ParseMode.MARKDOWN
        )
    else:
        tmp_result = {}
        async with aiohttp.ClientSession() as session:
            category_ids = await list_category_ids(session)
            msg = f"取得 {len(category_ids)} 個 category"
            logger.info(msg)
            await bot.edit_message_text(
                chat_id=reply_msg.chat_id, message_id=reply_msg.message_id, text=msg, parse_mode=ParseMode.MARKDOWN
            )

            category_index = 0
            for category_id in category_ids:
                retry_count = 0
                category_index += 1
                while retry_count < 3:
                    try:
                        category_gift_ids = await list_category_gift_ids(session, category_id, target_rate)
                        tmp_msg = f"{category_index}. category {category_id} 取得 {len(category_gift_ids)} 個 gift"
                        logger.info(tmp_msg)
                        msg = f"{msg}\n{tmp_msg}"
                        await bot.edit_message_text(
                            chat_id=reply_msg.chat_id, message_id=reply_msg.message_id, text=msg, parse_mode=ParseMode.MARKDOWN
                        )
                        break
                    except:
                        retry_count += 1
                        await asyncio.sleep(0.05)

                tasks = []
                for category_gift_id in category_gift_ids:
                    task = asyncio.create_task(fetch_gift(session, category_gift_id))
                    tasks.append(task)

                responses = await asyncio.gather(*tasks)
                for response in responses:
                    gift = Gift.from_dict(response.get("result"))

                    if (
                        gift.period_type == "FIXED"
                        and gift.money_lock_days < SHORT_MONEY_LOCK_DAYS
                        and target_rate <= gift.earning_rate
                    ):
                        gift_description = f"{gift.earning_rate}%, ${gift.price}, 銷售至 {gift.gift_ended_time}, "

                        if gift.period_days:
                            gift_description = f"{gift_description}可兌換至銷售後 {gift.period_days} 天\n"
                        elif gift.gift_expiration_time:
                            gift_description = f"{gift_description}可兌換至 {gift.gift_expiration_time}\n"

                        gift_description = (
                            f"{gift_description}最後一天買的話，錢錢被卡 {gift.money_lock_days} 天, {gift.earning_delay_days}天後給點\n"
                            f"{gift.name}\n"
                            f"https://giftshop-tw.line.me/voucher/{gift.id}"
                        )

                        tmp_result[gift.id] = gift_description

        utc_now = datetime.utcnow()
        time_format = "%Y-%m-%d %H:%M:%S"
        utc_plus_8_now = utc_now.replace(tzinfo=pytz.utc).astimezone(TIMEZONE_TAIWAN).strftime(time_format)
        result_text = f"快取時間: {utc_plus_8_now}"
        if tmp_result:
            for value in tmp_result.values():
                result_text = f"{result_text}\n---\n{value}"
        else:
            result_text = f"快取時間: {utc_plus_8_now}\n---\n查無結果"

        CACHE[target_rate] = result_text

        await bot.edit_message_text(
            chat_id=reply_msg.chat_id, message_id=reply_msg.message_id, text=result_text, parse_mode=ParseMode.MARKDOWN
        )
