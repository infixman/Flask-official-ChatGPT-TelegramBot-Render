import locale
import random

from telegram import Message, Update

from app.enum.sticker_type import StickerType

STICKER_TYPE_ID_MAPPING = {
    StickerType.PA: ["CAACAgUAAxkBAAEBLAJgd99sMMuqwAfwa9FOzEtglxLn4AAClwIAArjQcVewe5BU0CNqSB8E"],
    StickerType.BONBON: ["CAACAgIAAxkBAAEBLAVgd-FvoMW8F3nVGqx0nOUyxIF-qAACYQQAAonq5QdmC3mfOHu_3h8E"],
    StickerType.SOHA: ["CAACAgUAAxkBAAEBLAhgd-Grf4bTcZXHaHLUjOtNZMx3cwACNwQAAhwmkVfJpMRsyVY09B8E"],
}

TEXT_STICKER_MAPPING = {
    "啪": STICKER_TYPE_ID_MAPPING[StickerType.PA],
    "沒了": STICKER_TYPE_ID_MAPPING[StickerType.PA],
    "崩崩": STICKER_TYPE_ID_MAPPING[StickerType.BONBON],
    "梭哈": STICKER_TYPE_ID_MAPPING[StickerType.SOHA],
}

STICKER_WOBUZHIDAO = "CAACAgUAAxkBAAEBLBFgd_tZGLLQLj5O7kuE-r7chp_LOAAC_wEAAmmSQVVx1ECQ0wcNAh8E"


async def reply(update: Update):
    if update.message:
        msg: Message = update.message
        if msg.text:
            txt = str(msg.text).strip()
            if txt in TEXT_STICKER_MAPPING:
                sticker_id = random.choice(TEXT_STICKER_MAPPING[txt])
                await msg.reply_sticker(sticker_id)
            elif (txt.endswith("=?") or txt.endswith("=$?") or txt.endswith("=$")) and (
                "+" in txt or "-" in txt or "*" in txt or "/" in txt or "^" in txt
            ):
                fomula = txt.split("=")[0].strip().replace("^", "**")
                try:
                    if txt.endswith("=$?") or txt.endswith("=$"):
                        locale.setlocale(locale.LC_ALL, "en_US.utf8")
                        result = locale.format_string("%.2f", eval(fomula), grouping=True)
                        await msg.reply_text(f"={result}")
                    else:
                        await msg.reply_text(f"={eval(fomula)}")
                except:
                    await msg.reply_sticker(STICKER_WOBUZHIDAO)
