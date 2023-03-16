import json
import logging
import os
from datetime import datetime, timedelta, timezone

import requests
from bs4 import BeautifulSoup

LOG_LEVEL = os.getenv("LOG_LEVEL", default="INFO")

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=LOG_LEVEL)
logger = logging.getLogger(__name__)

def get_bito_price(utc_now: datetime):
    try:
        to_time = int(utc_now.timestamp())
        from_time = int((utc_now - timedelta(seconds=1800)).timestamp())
        r = requests.get(f"https://api.bitopro.com/v3/trading-history/usdt_twd?resolution=1m&from={from_time}&to={to_time}")
        obj = json.loads(r.text)
        if obj["data"] is None:
            return -1
        else:
            return float(obj["data"][0]["close"])
    except:
        return -1

def get_ace_price():
    try:
        r = requests.get("https://www.ace.io/polarisex/quote/getKline?baseCurrencyId=1&tradeCurrencyId=14&limit=1")
        obj = json.loads(r.text)
        if not obj["attachment"]:
            return -1
        else:
            return float(obj["attachment"][0]["closePrice"])
    except:
        return -1

def get_max_price():
    try:
        headers = {
            "authority": "max.maicoin.com",
            "cache-control": "no-cache",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) ",
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br",
            "connection": "keep-alive",
        }
        r = requests.get("https://max-api.maicoin.com/api/v2/trades?market=usdttwd", headers=headers)
        obj = json.loads(r.text)
        if obj:
            return float(obj[0]["price"])
        else:
            return -1
    except:
        return -1

def get_usd_rete_from_3rd():
    r = requests.get("https://www.bestxrate.com/card/mastercard/usd.html")
    soup = BeautifulSoup(r.text, "html.parser")
    masterCardRate = (
        [
            i.text
            for i in soup.select(
                "body > div > div:nth-child(3) > div > div > div.panel-body > div:nth-child(4) > div.col-md-10.col-xs-7 > b"
            )
        ][0]
        .replace("\xa0", "")
        .strip("0")
    )
    visaRate = [i.text for i in soup.select("#comparison_huilv_Visa")][0].strip("0")
    jcbRate = [i.text for i in soup.select("#comparison_huilv_JCB")][0].strip("0")
    return [masterCardRate, visaRate, jcbRate]

def get_usd_rate_esunbank():
    try:
        headers = {
            "Content-Type": "application/json",
            "Referer": "https://www.esunbank.com.tw/bank/personal/deposit/rate/forex/foreign-exchange-rates",
            "Host": "www.esunbank.com.tw",
        }

        response = requests.post(
            "https://www.esunbank.com.tw/api/client/ExchangeRate/LastRateInfo?sc_lang=en",
            headers=headers,
        )

        obj = json.loads(response.text)
        if obj:
            rates = obj["Rates"]
            result = list(filter(lambda x: x["Name"] == "美元", rates))
            if not result:
                return -1
            else:
                return result[0]["BuyIncreaseRate"]
        else:
            return -1
    except Exception as e:
        logger.info('except "%s"', e)
        return -1

def get_usd_rate():
    usd_rate = get_usd_rete_from_3rd()
    esun_usd_rate = get_usd_rate_esunbank()
    return f"USD Rate\n[BUY]\nMastercard: {usd_rate[0]} TWD\nVisa: {usd_rate[1]} TWD\nJCB: {usd_rate[2]} TWD\n[SELL]\n玉山網銀: {esun_usd_rate} TWD"

def get_usdt():
    utc_now = datetime.now(timezone.utc)
    bito_price = str(get_bito_price(utc_now))
    if bito_price == "-1":
        bito_price = "死了(?)"
    else:
        bito_price = bito_price + " TWD"
    ace_price = str(get_ace_price())
    if ace_price == "-1":
        ace_price = "死了(?)"
    else:
        ace_price = ace_price + " TWD"
    max_price = str(get_max_price())
    if max_price == "-1":
        max_price = "死了(?)"
    else:
        max_price = max_price + " TWD"
    return f"USDT Price\nBitoPro: {bito_price}\nAce: {ace_price}\nMax: {max_price}"