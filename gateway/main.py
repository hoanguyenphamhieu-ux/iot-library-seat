"""Gateway: doc du lieu tu bridge (Serial) va day len CoreIOT (buoc B3).

Chay:  python main.py
Dung:  Ctrl+C
"""
import logging
import time

import config
from serial_link import SerialLink
from tb_client import TBGateway, now_ms

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)-6s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("main")

TELEMETRY_KEYS = ("state", "ai", "conf", "tof", "obj_secs", "rssi")


class Gateway:
    def __init__(self):
        self.tb = TBGateway(config.TB_HOST, config.TB_PORT, config.TB_TOKEN)
        self.link = SerialLink(config.SERIAL_URL)
        self.states = {}        # seat -> state hien tai
        self.seq = {}           # seat -> {"last", "received", "missing"} trong cua so 60 giay
        self.last_loss_report = time.time()

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

        values = {k: msg[k] for k in TELEMETRY_KEYS if k in msg}
        self.tb.send_telemetry(seat, values, ts=now_ms())   # gan ts luc nhan
        self.track_seq(seat, msg.get("seq"))

        old = self.states.get(seat)
        self.states[seat] = msg.get("state")
        if old != self.states[seat]:
            log.info("%s: %s -> %s", seat, old, self.states[seat])
            self.send_room()

    def on_ack(self, msg):
        log.info("ACK tu %s rid=%s ok=%s (xu ly o buoc B4)", msg.get("seat"), msg.get("rid"), msg.get("ok"))

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

    # ---------- vong lap chinh ----------
    def run(self):
        self.tb.start()
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