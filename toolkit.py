"""Pure transform functions for CipherBot — no Telegram, no I/O, easy to test."""

from __future__ import annotations

import base64
import hashlib
import re
import secrets
import string
import urllib.parse
import uuid

# ─────────────────────────── ciphers ───────────────────────────


def rot13(text: str) -> str:
    return caesar(text, 13)


def caesar(text: str, shift: int) -> str:
    out = []
    for ch in text:
        if "a" <= ch <= "z":
            out.append(chr((ord(ch) - 97 + shift) % 26 + 97))
        elif "A" <= ch <= "Z":
            out.append(chr((ord(ch) - 65 + shift) % 26 + 65))
        else:
            out.append(ch)
    return "".join(out)


def atbash(text: str) -> str:
    out = []
    for ch in text:
        if "a" <= ch <= "z":
            out.append(chr(219 - ord(ch)))  # 219 = ord('a') + ord('z')
        elif "A" <= ch <= "Z":
            out.append(chr(155 - ord(ch)))  # 155 = ord('A') + ord('Z')
        else:
            out.append(ch)
    return "".join(out)


def _vigenere(text: str, key: str, decrypt: bool) -> str:
    key = [c for c in key.lower() if c.isalpha()]
    if not key:
        raise ValueError("key must contain letters")
    out, ki = [], 0
    for ch in text:
        if ch.isalpha():
            k = ord(key[ki % len(key)]) - 97
            if decrypt:
                k = -k
            base = 97 if ch.islower() else 65
            out.append(chr((ord(ch) - base + k) % 26 + base))
            ki += 1
        else:
            out.append(ch)
    return "".join(out)


def vigenere_encode(key: str, text: str) -> str:
    return _vigenere(text, key, decrypt=False)


def vigenere_decode(key: str, text: str) -> str:
    return _vigenere(text, key, decrypt=True)


MORSE = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".", "F": "..-.",
    "G": "--.", "H": "....", "I": "..", "J": ".---", "K": "-.-", "L": ".-..",
    "M": "--", "N": "-.", "O": "---", "P": ".--.", "Q": "--.-", "R": ".-.",
    "S": "...", "T": "-", "U": "..-", "V": "...-", "W": ".--", "X": "-..-",
    "Y": "-.--", "Z": "--..", "0": "-----", "1": ".----", "2": "..---",
    "3": "...--", "4": "....-", "5": ".....", "6": "-....", "7": "--...",
    "8": "---..", "9": "----.", ".": ".-.-.-", ",": "--..--", "?": "..--..",
    "!": "-.-.--", "/": "-..-.", "@": ".--.-.", "-": "-....-",
}
MORSE_REV = {v: k for k, v in MORSE.items()}


def morse_encode(text: str) -> str:
    words = text.upper().split(" ")
    return " / ".join(" ".join(MORSE.get(c, "?") for c in word if c) for word in words)


def morse_decode(code: str) -> str:
    words = code.strip().split(" / ") if " / " in code else code.strip().split("/")
    out = []
    for word in words:
        letters = [MORSE_REV.get(sym, "") for sym in word.split()]
        out.append("".join(letters))
    return " ".join(out).strip()


LEET = {"a": "4", "e": "3", "i": "1", "o": "0", "s": "5", "t": "7", "b": "8", "g": "9", "l": "1"}


def leet(text: str) -> str:
    return "".join(LEET.get(c.lower(), c) for c in text)


# ─────────────────────────── encodings ───────────────────────────


def b64_encode(text: str) -> str:
    return base64.b64encode(text.encode()).decode()


def b64_decode(text: str) -> str:
    return base64.b64decode(text.encode(), validate=True).decode("utf-8", "replace")


def hex_encode(text: str) -> str:
    return text.encode().hex()


def hex_decode(text: str) -> str:
    return bytes.fromhex(text.replace(" ", "")).decode("utf-8", "replace")


def bin_encode(text: str) -> str:
    return " ".join(format(b, "08b") for b in text.encode())


def bin_decode(text: str) -> str:
    bits = text.split()
    return bytes(int(b, 2) for b in bits).decode("utf-8", "replace")


def url_encode(text: str) -> str:
    return urllib.parse.quote(text)


def url_decode(text: str) -> str:
    return urllib.parse.unquote(text)


# ─────────────────────────── hashing ───────────────────────────


def md5(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


def sha1(text: str) -> str:
    return hashlib.sha1(text.encode()).hexdigest()


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


# ─────────────────────────── generators ───────────────────────────


def gen_password(length: int = 16) -> str:
    length = max(8, min(length, 128))
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*-_=+?"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def gen_uuid() -> str:
    return str(uuid.uuid4())


# ─────────────────────────── auto-detect ───────────────────────────


def _looks_text(s: str) -> bool:
    if not s:
        return False
    printable = sum(1 for c in s if c.isprintable() or c in "\n\t")
    return printable / len(s) > 0.85


def detect(text: str) -> list[tuple[str, str]]:
    """Best-effort: return [(method, decoded)] guesses for an unknown string."""
    t = text.strip()
    guesses: list[tuple[str, str]] = []

    if re.fullmatch(r"[01\s]+", t) and len(t.replace(" ", "")) >= 8:
        try:
            d = bin_decode(t)
            if _looks_text(d):
                guesses.append(("binary", d))
        except Exception:
            pass

    if re.fullmatch(r"[.\-/ ]+", t) and ("." in t or "-" in t):
        try:
            d = morse_decode(t)
            if d:
                guesses.append(("morse", d))
        except Exception:
            pass

    cleaned = t.replace(" ", "")
    if re.fullmatch(r"[0-9a-fA-F]+", cleaned) and len(cleaned) % 2 == 0 and len(cleaned) >= 4:
        try:
            d = hex_decode(cleaned)
            if _looks_text(d):
                guesses.append(("hex", d))
        except Exception:
            pass

    if re.fullmatch(r"[A-Za-z0-9+/]+={0,2}", t) and len(t) % 4 == 0 and len(t) >= 4:
        try:
            d = b64_decode(t)
            if _looks_text(d):
                guesses.append(("base64", d))
        except Exception:
            pass

    # always offer rot13 as a fallback hint
    guesses.append(("rot13", rot13(t)))

    # de-dup by (method) keeping order
    seen, uniq = set(), []
    for m, d in guesses:
        if m not in seen:
            seen.add(m)
            uniq.append((m, d))
    return uniq
