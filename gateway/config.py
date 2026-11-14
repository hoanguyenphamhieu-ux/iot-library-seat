"""Doc cau hinh tu file .env (nam cung thu muc voi file nay)."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))


def _require(name):
    value = os.getenv(name, "").strip()
    if not value or value.startswith("<") or value.startswith("dan_"):
        raise SystemExit(f"[config] Thieu {name} trong gateway/.env - mo file .env va dien vao.")
    return value


TB_HOST = _require("TB_HOST")
TB_PORT = int(os.getenv("TB_PORT", "1883"))
TB_TOKEN = _require("TB_TOKEN")
SERIAL_URL = _require("SERIAL_URL")

SEAT_PROFILE = "library-seat"   # CONTRACT 3.1
ROOM_DEVICE = "Room-A"
ROOM_PROFILE = "room"
LOSS_WINDOW_SEC = 60            # CONTRACT 3.4: loss_pct tinh moi 60 giay