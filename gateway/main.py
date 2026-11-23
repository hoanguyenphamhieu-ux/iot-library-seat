"""Gateway: doc du lieu tu bridge (Serial) va day len CoreIOT (buoc B3).

Chay:  python main.py
Dung:  Ctrl+C
"""
# cầu nối giữa hai file serial_link và tb_client. Với mỗi dòng bridge gửi lên, 
# nó quyết định làm gì: lưu lại, gửi CoreIOT, tính loss_pct, đếm free_seats.
# Nó cũng nhận RPC, ghi lệnh xuống bridge và đợi ACK. Quá 5 giây không có ACK thì trả success:false
import csv
import logging
import threading
import time

import ai_job
import config
from serial_link import SerialLink
from store import Store
from tb_client import TBGateway, now_ms
from web.app import create_app

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)-6s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("main")

TELEMETRY_KEYS = ("state", "ai", "conf", "tof", "obj_secs", "rssi")
RPC_TO_CMD = {"setWarning": "warn", "enterOta": "ota"}   # CONTRACT 3.5


class Gateway:
    def __init__(self):
        self.store = Store(config.DB_PATH)                                     # B5
        self.tb = TBGateway(config.TB_HOST, config.TB_PORT, config.TB_TOKEN, store=self.store)
        self.link = SerialLink(config.SERIAL_URL)
        self.states = {}        # seat -> state hien tai
        self.latest = {}        # seat -> ban tin telemetry moi nhat (cho trang web)
        self.hog = {}           # seat -> ket qua AI gan nhat (B7)
        self.stats = {}         # seat -> {"usage_pct", "hog_count"} trong ngay (B7)
        self.offline_warned = set()   # ghe da duoc gateway tu bat canh bao luc mat mang
        self.seq = {}           # seat -> {"last", "received", "missing"} trong cua so 60 giay
        self.last_loss_report = time.time()

        # pending: rid -> {"device","tb_id","method","t0"}; tb_id=None nghia la lenh tu trang web local
        self.pending = {}
        self.local_results = {}           # rid -> ok (ket qua lenh tu trang web, web cho doc)
        self.next_rid = 0
        self.lock = threading.Lock()      # on_rpc/web chay o thread khac, on_ack chay o vong lap chinh
        self.tb.on_rpc = self.on_rpc

    # ---------- xu ly tung loai dong tu bridge ----------
    def on_hello(self, msg):
        seat = msg["seat"]
        self.tb.connect_device(seat, config.SEAT_PROFILE)
        self.tb.send_telemetry(seat, {
            "current_fw_title": "seat-node",
            "current_fw_version": msg.get("fw", "unknown"),
        })
        self.seq[seat] = {"last": None, "received": 0, "missing": 0}   # node khoi dong lai -> seq ve 0

    def on_telemetry(self, msg):
        seat = msg["seat"]
        if seat not in self.tb.devices:          # gateway khoi dong sau bridge -> chua thay hello
            self.on_hello({"seat": seat, "fw": msg.get("fw", "unknown")})

        ts = now_ms()                            # gan ts luc nhan
        values = {k: msg[k] for k in TELEMETRY_KEYS if k in msg}
        self.store.add_reading(ts, seat, msg)                 # B5: luu local truoc
        self.latest[seat] = {**values, "ts": ts}
        self.tb.send_telemetry(seat, values, ts=ts)           # mat mang -> tu vao outbox
        self.track_seq(seat, msg.get("seq"))

        old = self.states.get(seat)
        self.states[seat] = msg.get("state")
        if old != self.states[seat]:
            log.info("%s: %s -> %s", seat, old, self.states[seat])
            self.send_room()

    def on_ack(self, msg):
        self.finish_rpc(msg.get("rid"), bool(msg.get("ok")))

    # ---------- gui lenh xuong ghe ----------
    def _send_cmd(self, device, cmd, on, tb_id, method):
        """Cap rid, ghi dong cmd ra Serial. Tra ve rid, hoac None neu khong ghi duoc Serial."""
        with self.lock:
            self.next_rid = self.next_rid % 65535 + 1      # rid la uint16 trong CmdPacket
            rid = self.next_rid
            self.pending[rid] = {"device": device, "tb_id": tb_id, "method": method, "t0": time.time()}
        line = {"type": "cmd", "seat": device, "cmd": cmd, "rid": rid}
        if cmd == "warn":
            line["on"] = 1 if on else 0
        if self.link.write_json(line):
            return rid
        self.finish_rpc(rid, False, "(khong ghi duoc Serial)")
        return None

    # RPC tu CoreIOT xuong ghe (B4)
    def on_rpc(self, payload):
        device = payload.get("device")
        data = payload.get("data") or {}
        tb_id, method, params = data.get("id"), data.get("method"), data.get("params") or {}
        if method is None:                   # khong phai yeu cau RPC (vd. ban tin tra loi bi doi lai) -> bo qua
            return
        cmd = RPC_TO_CMD.get(method)
        if device is None or tb_id is None or cmd is None:
            log.warning("RPC khong hop le hoac khong ho tro: %s", payload)
            if device is not None and tb_id is not None:
                self.tb.send_rpc_reply(device, tb_id, {"success": False})
            return
        rid = self._send_cmd(device, cmd, params.get("on"), tb_id, method)
        if rid is not None:
            log.info("RPC %s -> %s rid=%d", method, device, rid)

    # lenh tu trang web local (B6): ghi thang Serial, KHONG di qua CoreIOT nen mat mang van chay
    def send_local_cmd(self, device, cmd, on=0):
        """Tra ve (rid, ok): cho toi da RPC_TIMEOUT_SEC giay de co ACK. rid=None neu khong ghi duoc Serial."""
        rid = self._send_cmd(device, cmd, on, None, "local-" + cmd)
        if rid is None:
            return None, False
        deadline = time.time() + config.RPC_TIMEOUT_SEC + 1
        while time.time() < deadline:
            with self.lock:
                if rid in self.local_results:
                    return rid, self.local_results.pop(rid)
            time.sleep(0.05)
        return rid, False

    def finish_rpc(self, rid, ok, note=""):
        with self.lock:
            item = self.pending.pop(rid, None)
        if item is None:                      # ACK muon sau khi da timeout, hoac rid la
            return
        ms = (time.time() - item["t0"]) * 1000
        if item["tb_id"] is None:             # lenh tu web hoac tu canh bao khi mat mang
            if item["method"].startswith("local-"):       # chi lenh tu web co nguoi cho ket qua
                with self.lock:
                    self.local_results[rid] = ok
        else:                                 # lenh tu CoreIOT
            self.tb.send_rpc_reply(item["device"], item["tb_id"], {"success": ok})
            self.log_rpc_latency(item, ok, ms)
        log.info("CMD rid=%d %s %s ok=%s latency=%.0f ms %s", rid, item["device"], item["method"], ok, ms, note)

    def log_rpc_latency(self, item, ok, ms):
        """M3: ghi 1 dong vao docs/measurements/rpc_latency.csv (do tren gateway: nhan RPC -> co ACK)."""
        try:
            path = config.RPC_LOG_PATH
            path.parent.mkdir(parents=True, exist_ok=True)
            new = not path.exists()
            with open(path, "a", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                if new:
                    w.writerow(["time", "device", "method", "ok", "latency_ms"])
                w.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), item["device"], item["method"], int(ok), round(ms)])
        except OSError as e:
            log.warning("Khong ghi duoc rpc_latency.csv: %s", e)

    def expire_pending(self):
        now = time.time()
        with self.lock:
            late = [rid for rid, it in self.pending.items() if now - it["t0"] > config.RPC_TIMEOUT_SEC]
        for rid in late:
            self.finish_rpc(rid, False, "(timeout)")
    # ---------- canh bao khi mat mang ----------
    def offline_warning(self):
        """Mat ket noi CoreIOT thi rule chain khong chay duoc -> gateway tu ap dung cung quy tac:
        OBJECT_ONLY va obj_secs >= HOG_LIMIT_SEC -> warn on; ghe doi trang thai khac -> warn off."""
        if self.tb.is_connected():
            self.offline_warned.clear()       # co mang lai: rule chain tiep quan
            return
        now = now_ms()
        for seat, v in self.latest.items():
            if now - v["ts"] > config.OFFLINE_WARN_STALE_SEC * 1000:
                continue                      # ghe khong gui gi nua, khong du can cu
            hogging = v.get("state") == "OBJECT_ONLY" and (v.get("obj_secs") or 0) >= config.HOG_LIMIT_SEC
            if hogging and seat not in self.offline_warned:
                if self._send_cmd(seat, "warn", 1, None, "auto-warn") is not None:
                    self.offline_warned.add(seat)
                    log.warning("%s: mat mang, tu bat canh bao (obj_secs=%s)", seat, v.get("obj_secs"))
            elif not hogging and seat in self.offline_warned:
                if self._send_cmd(seat, "warn", 0, None, "auto-warn") is not None:
                    self.offline_warned.discard(seat)
                    log.info("%s: da het giu cho, tu tat canh bao", seat)

    # ---------- tinh toan ----------
    def track_seq(self, seat, seq):
        if seq is None:
            return
        s = self.seq.setdefault(seat, {"last": None, "received": 0, "missing": 0})
        if s["last"] is not None and seq > s["last"] + 1:
            s["missing"] += seq - s["last"] - 1
        s["last"] = seq
        s["received"] += 1

    def report_loss(self):
        for seat, s in self.seq.items():
            expected = s["received"] + s["missing"]
            if expected == 0:
                continue
            loss = round(100.0 * s["missing"] / expected, 2)
            self.tb.send_telemetry(seat, {"loss_pct": loss})
            log.info("%s loss_pct=%.2f%% (%d/%d goi mat)", seat, loss, s["missing"], expected)
            s["received"] = s["missing"] = 0

    def send_room(self):
        free = sum(1 for st in self.states.values() if st == "EMPTY")
        self.tb.send_telemetry(config.ROOM_DEVICE, {"free_seats": free})

    # ---------- thread phu ----------
    def start_web(self):
        app = create_app(self)
        # use_reloader=False: neu bat reloader Flask se chay main.py hai lan
        t = threading.Thread(
            target=lambda: app.run(host=config.WEB_HOST, port=config.WEB_PORT, threaded=True, use_reloader=False),
            daemon=True, name="web")
        t.start()
        log.info("Web local: http://localhost:%d", config.WEB_PORT)

    def start_ai(self):
        t = threading.Thread(target=ai_job.loop, args=(self,), daemon=True, name="ai")
        t.start()
    # ---------- vong lap chinh ----------
    def run(self):
        self.tb.start()
        self.start_web()
        self.start_ai()
        for _ in range(15):                      # cho toi da 15 giay cho MQTT ket noi xong
            if self.tb.is_connected():
                break
            time.sleep(1)
        else:
            log.warning("Chua ket noi duoc CoreIOT sau 15 giay - kiem tra TB_HOST/TB_TOKEN. Van tiep tuc doc Serial.")
        self.tb.connect_device(config.ROOM_DEVICE, config.ROOM_PROFILE)
        handlers = {"hello": self.on_hello, "telemetry": self.on_telemetry, "ack": self.on_ack}

        for msg in self.link.messages():
            if msg is not None:
                handler = handlers.get(msg.get("type"))
                if handler is None:
                    log.warning("Loai dong khong biet: %s", msg)
                elif "seat" not in msg:
                    log.warning("Thieu truong seat: %s", msg)
                else:
                    handler(msg)

            self.expire_pending()
            self.offline_warning()                               # B4: tu canh bao khi mat mang
            self.tb.flush_outbox(config.OUTBOX_BATCH)            # B5: co mang lai thi gui bu
            if time.time() - self.last_loss_report >= config.LOSS_WINDOW_SEC:
                self.report_loss()
                self.last_loss_report = time.time()


if __name__ == "__main__":
    gw = Gateway()
    try:
        gw.run()
    except KeyboardInterrupt:
        log.info("Dung gateway.")
        gw.tb.stop()