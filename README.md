# 🛰 CipherBot

> A pocket **cyber-toolkit** for Telegram — ciphers, encodings, hashes, auto-detect,
> generators, and an inline mode that works in any chat. Zero paid APIs, fully offline.

Built for geeks and CTF players. Throw it a weird string and it tries to crack it.

## Features

- **Ciphers** — ROT13, Caesar (any shift), Vigenère (encode/decode), Atbash, Morse, Leetspeak
- **Encodings** — Base64, Hex, Binary, URL — both directions
- **Hashes** — MD5, SHA-1, SHA-256
- **Auto-detect** — send any mystery string; the bot guesses Base64 / Hex / Binary / Morse and decodes it
- **Generators** — strong passwords, UUIDs, **QR codes** (sent as an image)
- **Inline mode** — in *any* chat: `@your_bot rot13 hello` → result inline
- **Reply support** — reply to a message with a bare command (e.g. `/b64`) to transform its text

## Commands

```
/rot13  /atbash  /leet
/caesar <shift> <text>
/vig <key> <text>      /unvig <key> <text>
/morse  /unmorse
/b64 /unb64  /hex /unhex  /bin /unbin  /url /unurl
/md5 /sha1 /sha256
/pass [length]   /uuid   /qr <text|url>
/detect <string>
```

## Setup

1. Create a bot with [@BotFather](https://t.me/BotFather) → grab the token.
2. (Optional, for inline mode) in BotFather: `/setinline` → pick your bot → set a placeholder.
3. Install & run:

```bash
python -m pip install -r requirements.txt
cp .env.example .env          # then paste your token into .env
python bot.py
```

The bot uses long polling — no server or webhook needed. Keep `python bot.py`
running (locally, on a VPS, or in a `screen`/`tmux`/systemd unit).

## Run 24/7 with Docker

The bot is a long-polling worker — no exposed ports. Put your token in `.env`
(see `.env.example`), then:

```bash
docker compose up -d --build      # build + run in the background
docker compose logs -f            # watch the logs
docker compose down               # stop
```

Or with plain Docker:

```bash
docker build -t cipherbot .
docker run -d --restart unless-stopped --env-file .env --name cipherbot cipherbot
```

`restart: unless-stopped` keeps it alive across reboots. The token is passed at
runtime via `.env` and is **never** baked into the image (`.env` is in both
`.gitignore` and `.dockerignore`).

> If your host routes traffic through a SOCKS proxy you actually need, run with
> `-e USE_PROXY=1` and a proxy scheme httpx supports (`socks5://`).

## Project layout

```
cipherbot/
├─ bot.py            # Telegram handlers (commands, inline, auto-detect)
├─ toolkit.py        # pure transform functions (no Telegram) — easy to test
├─ requirements.txt
├─ .env.example
└─ README.md
```

`toolkit.py` has no Telegram dependency, so every transform is unit-testable in
isolation.

## License

MIT
