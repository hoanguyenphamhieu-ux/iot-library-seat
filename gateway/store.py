"""SQLite cuc bo (B5): luu readings de ve bieu do/AI, va outbox de gui bu khi mat mang.

File gateway.db nam canh file nay (da bi .gitignore chan: *.db).
Nhieu thread cung dung (main ghi, Flask doc, AI doc) nen moi thao tac deu qua self.lock.
"""
import sqlite3
import threading

SCHEMA = """
CREATE TABLE IF NOT EXISTS readings (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    ts       INTEGER NOT NULL,           -- mili-giay, luc gateway nhan
    seat     TEXT    NOT NULL,
    state    TEXT,
    ai       TEXT,
    conf     REAL,
    tof      INTEGER,
    obj_secs INTEGER,
    rssi     INTEGER
);
CREATE INDEX IF NOT EXISTS idx_readings_seat_ts ON readings(seat, ts);

CREATE TABLE IF NOT EXISTS outbox (          -- ban tin telemetry CHUA gui duoc len CoreIOT
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    topic   TEXT NOT NULL,
    payload TEXT NOT NULL                    -- JSON da co san ts goc cua luc do doc
);
"""
#bộ nhớ SQLite trong file gateway.db, gồm hai bảng. 
#readings ghi mọi số liệu đã nhận (cho web vẽ biểu đồ và AI phân tích). outbox là hàng chờ gửi bù

class Store:
    def __init__(self, path):
        # check_same_thread=False: cho phep nhieu thread dung chung 1 ket noi (da co lock bao ve)
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.lock = threading.Lock()
        with self.lock:
            self.db.executescript(SCHEMA)
            self.db.commit()

    # ---------- readings ----------
    def add_reading(self, ts, seat, msg):
        with self.lock:
            self.db.execute(
                "INSERT INTO readings(ts,seat,state,ai,conf,tof,obj_secs,rssi) VALUES(?,?,?,?,?,?,?,?)",
                (ts, seat, msg.get("state"), msg.get("ai"), msg.get("conf"),
                 msg.get("tof"), msg.get("obj_secs"), msg.get("rssi")))
            self.db.commit()

    def readings_since(self, seat, ts_from):
        """Tra ve list dict, cu -> moi, cua mot ghe tu moc ts_from (ms)."""
        with self.lock:
            cur = self.db.execute(
                "SELECT ts,state,ai,conf,tof,obj_secs,rssi FROM readings "
                "WHERE seat=? AND ts>=? ORDER BY ts", (seat, ts_from))
            rows = cur.fetchall()
        keys = ("ts", "state", "ai", "conf", "tof", "obj_secs", "rssi")
        return [dict(zip(keys, r)) for r in rows]

    def seats(self):
        with self.lock:
            return [r[0] for r in self.db.execute("SELECT DISTINCT seat FROM readings ORDER BY seat")]

    # ---------- outbox ----------
    def outbox_add(self, topic, payload_json):
        with self.lock:
            self.db.execute("INSERT INTO outbox(topic,payload) VALUES(?,?)", (topic, payload_json))
            self.db.commit()

    def outbox_take(self, limit):
        """Lay toi da `limit` ban tin cu nhat (chua xoa)."""
        with self.lock:
            return self.db.execute(
                "SELECT id,topic,payload FROM outbox ORDER BY id LIMIT ?", (limit,)).fetchall()

    def outbox_delete(self, ids):
        if not ids:
            return
        with self.lock:
            self.db.executemany("DELETE FROM outbox WHERE id=?", [(i,) for i in ids])
            self.db.commit()

    def outbox_count(self):
        with self.lock:
            return self.db.execute("SELECT COUNT(*) FROM outbox").fetchone()[0]

    def close(self):
        with self.lock:
            self.db.close()
