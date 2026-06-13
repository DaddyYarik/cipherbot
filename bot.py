"""CipherBot — a pocket cyber-toolkit for Telegram (ciphers, encodings, hashes)."""

from __future__ import annotations

import html
import io
import logging
import os
from uuid import uuid4

from dotenv import load_dotenv
from telegram import (
    InlineQueryResultArticle,
    InputTextMessageContent,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    InlineQueryHandler,
    MessageHandler,
    filters,
)

import toolkit as tk

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s", level=logging.INFO
)
log = logging.getLogger("cipherbot")

# command name -> (pretty label, unary str->str function)
UNARY: dict[str, tuple[str, callable]] = {
    "rot13": ("🔄 ROT13", tk.rot13),
    "atbash": ("🪞 Atbash", tk.atbash),
    "leet": ("🅻 Leet", tk.leet),
    "morse": ("📡 Morse", tk.morse_encode),
    "unmorse": ("📡 Morse → text", tk.morse_decode),
    "b64": ("📦 Base64", tk.b64_encode),
    "unb64": ("📦 Base64 → text", tk.b64_decode),
    "hex": ("🔢 Hex", tk.hex_encode),
    "unhex": ("🔢 Hex → text", tk.hex_decode),
    "bin": ("💾 Binary", tk.bin_encode),
    "unbin": ("💾 Binary → text", tk.bin_decode),
    "url": ("🌐 URL-encode", tk.url_encode),
    "unurl": ("🌐 URL-decode", tk.url_decode),
    "md5": ("#️⃣ MD5", tk.md5),
    "sha1": ("#️⃣ SHA-1", tk.sha1),
    "sha256": ("#️⃣ SHA-256", tk.sha256),
}

HELP = """<b>🛰 CipherBot</b> — твой карманный кибер-тулкит.

<b>Шифры</b>
/rot13 · /atbash · /leet
/caesar &lt;сдвиг&gt; &lt;текст&gt;
/vig &lt;ключ&gt; &lt;текст&gt; · /unvig &lt;ключ&gt; &lt;текст&gt;
/morse · /unmorse

<b>Кодировки</b>
/b64 · /unb64 · /hex · /unhex · /bin · /unbin · /url · /unurl

<b>Хеши</b>
/md5 · /sha1 · /sha256

<b>Генераторы</b>
/pass [длина] · /uuid · /qr &lt;текст или ссылка&gt;

<b>Авто-детект</b>
/detect &lt;строка&gt; — или просто пришли непонятный текст, я попробую раскодировать.
🖼 Пришли <b>картинку с QR</b> — распознаю и верну содержимое.

💡 Можно <b>ответить</b> на сообщение командой без аргументов — возьму его текст.
😎 <b>Inline:</b> в любом чате напиши <code>@{username} rot13 привет</code>"""


def _input_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    if context.args:
        return " ".join(context.args)
    msg = update.effective_message
    if msg and msg.reply_to_message and msg.reply_to_message.text:
        return msg.reply_to_message.text
    return ""


def _fmt(label: str, out: str) -> str:
    return f"{label}\n<code>{html.escape(out)}</code>"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    username = (await context.bot.get_me()).username
    await update.effective_message.reply_html(HELP.format(username=username))


def make_unary(cmd: str, label: str, fn):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = _input_text(update, context)
        if not text:
            await update.effective_message.reply_text(
                f"Использование: /{cmd} <текст>  (или ответь командой на сообщение)"
            )
            return
        try:
            out = fn(text)
        except Exception as e:  # noqa: BLE001
            await update.effective_message.reply_text(f"⚠️ не вышло: {e}")
            return
        await update.effective_message.reply_html(_fmt(label, out))

    return handler


async def caesar_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if len(args) < 2 or not args[0].lstrip("-").isdigit():
        await update.effective_message.reply_text("Использование: /caesar <сдвиг> <текст>")
        return
    out = tk.caesar(" ".join(args[1:]), int(args[0]))
    await update.effective_message.reply_html(_fmt(f"🔐 Caesar ({args[0]})", out))


def make_vig(decrypt: bool, label: str):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        args = context.args
        if len(args) < 2:
            await update.effective_message.reply_text("Использование: /vig <ключ> <текст>")
            return
        key, text = args[0], " ".join(args[1:])
        try:
            out = tk.vigenere_decode(key, text) if decrypt else tk.vigenere_encode(key, text)
        except Exception as e:  # noqa: BLE001
            await update.effective_message.reply_text(f"⚠️ не вышло: {e}")
            return
        await update.effective_message.reply_html(_fmt(label, out))

    return handler


async def pass_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    length = 16
    if context.args and context.args[0].isdigit():
        length = int(context.args[0])
    await update.effective_message.reply_html(_fmt("🔑 Password", tk.gen_password(length)))


async def uuid_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_html(_fmt("🆔 UUID", tk.gen_uuid()))


async def qr_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = _input_text(update, context)
    if not text:
        await update.effective_message.reply_text(
            "Использование: /qr <текст или ссылка>  (или ответь командой на сообщение)"
        )
        return
    try:
        png = tk.qr_png(text)
    except Exception as e:  # noqa: BLE001  (e.g. data too long for a QR code)
        await update.effective_message.reply_text(f"⚠️ не вышло сделать QR: {e}")
        return
    photo = io.BytesIO(png)
    photo.name = "qr.png"
    caption = text if len(text) <= 120 else text[:117] + "…"
    await update.effective_message.reply_photo(photo=photo, caption=f"🔳 {html.escape(caption)}")


async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    file_id = None
    if msg.photo:
        file_id = msg.photo[-1].file_id  # largest size
    elif msg.document and (msg.document.mime_type or "").startswith("image/"):
        file_id = msg.document.file_id
    if not file_id:
        return
    tg_file = await context.bot.get_file(file_id)
    data = bytes(await tg_file.download_as_bytearray())
    try:
        text = tk.decode_qr(data)
    except Exception as e:  # noqa: BLE001
        await msg.reply_text(f"⚠️ не смог обработать картинку: {e}")
        return
    if text:
        await msg.reply_html(f"🔳 <b>QR найден:</b>\n<code>{html.escape(text)}</code>")
    else:
        await msg.reply_text("🔍 QR-код на картинке не распознан.")


async def detect_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = _input_text(update, context)
    if not text:
        await update.effective_message.reply_text("Использование: /detect <строка>")
        return
    await update.effective_message.reply_html(_detect_text(text))


def _detect_text(text: str) -> str:
    guesses = tk.detect(text)
    lines = [f"<b>{m}</b> → <code>{html.escape(d)}</code>" for m, d in guesses]
    return "🕵️ <b>Похоже на:</b>\n" + "\n".join(lines)


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.effective_message.text or ""
    if not text:
        return
    await update.effective_message.reply_html(_detect_text(text))


async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.inline_query.query.strip()
    results: list[InlineQueryResultArticle] = []

    def art(title: str, text: str) -> InlineQueryResultArticle:
        return InlineQueryResultArticle(
            id=str(uuid4()),
            title=title,
            description=text[:90],
            input_message_content=InputTextMessageContent(text),
        )

    if not q:
        results.append(
            art("Напиши: rot13 / b64 / hex / morse … и текст", "Пример: rot13 hello world")
        )
    else:
        parts = q.split(" ", 1)
        key = parts[0].lower()
        rest = parts[1] if len(parts) > 1 else ""

        if key in UNARY and rest:
            label, fn = UNARY[key]
            try:
                results.append(art(label, fn(rest)))
            except Exception:  # noqa: BLE001
                pass
        elif key == "caesar":
            sub = rest.split(" ", 1)
            if len(sub) == 2 and sub[0].lstrip("-").isdigit():
                results.append(art(f"🔐 Caesar ({sub[0]})", tk.caesar(sub[1], int(sub[0]))))

        if not results:
            for m, d in tk.detect(q)[:3]:
                results.append(art(f"🕵️ detect · {m}", d))
            for name in ("rot13", "b64", "hex"):
                label, fn = UNARY[name]
                try:
                    results.append(art(label, fn(q)))
                except Exception:  # noqa: BLE001
                    pass

    await update.inline_query.answer(results[:10], cache_time=1)


def main() -> None:
    load_dotenv()
    # Ignore any system proxy (env vars OR Windows registry) that httpx can't
    # parse, e.g. socks4://... . NO_PROXY="*" makes httpx connect directly to
    # every host. Direct connection to api.telegram.org works here.
    # Set USE_PROXY=1 to keep the system proxy instead.
    if os.environ.get("USE_PROXY") != "1":
        for var in ("ALL_PROXY", "all_proxy", "HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy"):
            os.environ.pop(var, None)
        os.environ["NO_PROXY"] = "*"
        os.environ["no_proxy"] = "*"

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit(
            "TELEGRAM_BOT_TOKEN не задан. Создай бота у @BotFather и положи токен в .env"
        )

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler(["start", "help"], start))
    for cmd, (label, fn) in UNARY.items():
        app.add_handler(CommandHandler(cmd, make_unary(cmd, label, fn)))
    app.add_handler(CommandHandler("caesar", caesar_cmd))
    app.add_handler(CommandHandler("vig", make_vig(False, "🔐 Vigenère")))
    app.add_handler(CommandHandler("unvig", make_vig(True, "🔐 Vigenère → text")))
    app.add_handler(CommandHandler("pass", pass_cmd))
    app.add_handler(CommandHandler("uuid", uuid_cmd))
    app.add_handler(CommandHandler("qr", qr_cmd))
    app.add_handler(CommandHandler("detect", detect_cmd))
    app.add_handler(InlineQueryHandler(inline_query))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, on_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    log.info("CipherBot is up. Polling…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
