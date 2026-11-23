"""Doc cau hinh tu file .env (nam cung thu muc voi file nay)."""
#đọc .env (host, token, cổng Serial) và chứa các hằng số như thời gian chờ, cổng web
import os       #doc bien moi truong
from pathlib import Path    #xu ly duong dan file

from dotenv import load_dotenv      #ham cua thu vien python-dotenv

# đọc từng dòng TÊN=giá_trị trong file rồi nạp vào biến môi trường của tiến trình
load_dotenv(Path(__file__).with_name(".env"))


def _require(name):
    value = os.getenv(name, "").strip() #lấy giá trị theo tên biến
    if not value or value.startswith("<") or value.startswith("dan_"): #chưa chỉnh gì bên env thì in báo lỗi và dừng ctrinh
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
RPC_TIMEOUT_SEC = 5            # CONTRACT 3.5: qua 5 giay khong co ACK thi tra success=false

# ---- B5-B7 ----
DB_PATH = Path(__file__).with_name("gateway.db")     # SQLite: readings + outbox (da nam trong .gitignore: *.db)
OUTBOX_BATCH = 100              # moi lan gui bu toi da bao nhieu ban tin
WEB_HOST = "127.0.0.1"          # chi may nay vao duoc (trang web khong co mat khau)
WEB_PORT = 5000
AI_INTERVAL_SEC = 300           # B7: chay AI moi 5 phut
AI_WINDOW_SEC = 1800            # B7: moi lan nhin lai 30 phut gan nhat
AI_MODEL_PATH = Path(__file__).with_name("hog_model.joblib")
RPC_LOG_PATH = Path(__file__).resolve().parent.parent / "docs" / "measurements" / "rpc_latency.csv"   # M3