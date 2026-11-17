"""
fake_bridge.py - Bridge gia lap de test gateway khi chua co phan cung.

Lam gi:
  - Mo TCP server o cong 7000 (gia lam cong Serial cua node bridge).
  - Khi gateway ket noi vao: gui 3 dong hello, sau do cu PERIOD giay gui
    telemetry cho Seat-01..03, dung dinh dang CONTRACT.md muc 3.3.
  - Nhan dong {"type":"cmd",...} tu gateway: in "# WARN ..." va tra ve dong ack.

Chay:
  python fake_bridge.py                 # nhip that: 10 giay/lan
  python fake_bridge.py --speed 10      # tua nhanh x10 de test RuleChain cho le
  python fake_bridge.py --port 7001     # doi cong neu 7000 bi chiem

Gateway ket noi bang: SERIAL_URL=socket://localhost:7000
"""
#bridge giả để test khi chưa có phần cứng. Nó giả vờ là cổng Serial (qua TCP 7000) và phát dữ liệu theo kịch bản.
import argparse
import json
import random
import socket
import threading
import time

SEATS = ["Seat-01", "Seat-02", "Seat-03"]
PERIOD = 10          # giay giua 2 lan heartbeat (CONTRACT 3.2)
DROP_RATE = 0.02     # 2% goi bi "mat" de gateway tinh loss_pct

# Kich ban co dinh cho Seat-01, tinh theo giay mo phong, lap lai moi 300 giay
SEAT01_SCRIPT = [
    (30, "EMPTY"),
    (60, "OCCUPIED"),
    (180, "OBJECT_ONLY"),   # obj_secs tang toi 180 -> du vuot hogLimitSec = 120
    (30, "OCCUPIED"),
]


class Seat:
    def __init__(self, name):
        self.name = name
        self.seq = 0
        self.state = "EMPTY"
        self.obj_since = None   # thoi diem mo phong bat dau OBJECT_ONLY
        self.fw = "1.0"
        self.warning = False

    def set_state(self, new_state, sim_t):
        if new_state != self.state:
            self.state = new_state
            self.obj_since = sim_t if new_state == "OBJECT_ONLY" else None

    def obj_secs(self, sim_t):
        if self.obj_since is None:
            return 0
        return int(sim_t - self.obj_since)

    def telemetry(self, sim_t):
        if self.state == "EMPTY":
            ai, tof = "empty", random.randint(440, 460)
        elif self.state == "OCCUPIED":
            ai, tof = random.choice(["person_still", "person_move"]), random.randint(220, 280)
        else:
            ai, tof = "bag", random.randint(210, 250)
        return {
            "type": "telemetry",
            "seat": self.name,
            "seq": self.seq,
            "state": self.state,
            "ai": ai,
            "conf": random.randint(75, 98),
            "tof": tof,
            "obj_secs": self.obj_secs(sim_t),
            "rssi": random.randint(-70, -40),
            "fw": self.fw,
        }


# Seat-02, Seat-03: hanh vi BINH THUONG (cho AI so sanh voi Seat-01 giu cho), lap lai moi 900 giay
SEAT02_SCRIPT = [(120, "EMPTY"), (600, "OCCUPIED"), (30, "OBJECT_ONLY"), (150, "OCCUPIED")]
SEAT03_SCRIPT = [(500, "EMPTY"), (300, "OCCUPIED"), (100, "EMPTY")]


def script_state_at(script, sim_t):
    cycle = sum(d for d, _ in script)
    t = sim_t % cycle
    for duration, state in script:
        if t < duration:
            return state
        t -= duration
    return script[-1][1]


def seat01_state_at(sim_t):
    return script_state_at(SEAT01_SCRIPT, sim_t)


class FakeBridge:
    def __init__(self, port, speed):
        self.port = port
        self.speed = speed
        self.seats = {name: Seat(name) for name in SEATS}
        self.start = time.time()
        self.conn = None
        self.send_lock = threading.Lock()

    def sim_time(self):
        return (time.time() - self.start) * self.speed

    # ---------- gui ----------
    def send_line(self, text):
        """Gui 1 dong toi gateway. Tra ve False neu gateway da ngat."""
        conn = self.conn
        if conn is None:
            return False
        try:
            with self.send_lock:
                conn.sendall((text + "\n").encode("utf-8"))
            return True
        except OSError:
            return False

    def send_json(self, obj):
        return self.send_line(json.dumps(obj, separators=(",", ":")))

    def log(self, text):
        """In ra man hinh va gui kem cho gateway (dong bat dau bang '#')."""
        print(text, flush=True)
        self.send_line(text)

    def send_hello(self, seat):
        return self.send_json({"type": "hello", "seat": seat.name, "fw": seat.fw})

    def send_telemetry(self, seat):
        seat.seq += 1
        if random.random() < DROP_RATE:
            print(f"# (gia lap mat goi {seat.name} seq={seat.seq})", flush=True)
            return True
        return self.send_json(seat.telemetry(self.sim_time()))

    # ---------- nhan lenh ----------
    def handle_command(self, line):
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            print(f"# Bo qua dong khong phai JSON: {line!r}", flush=True)
            return
        if msg.get("type") != "cmd":
            return
        seat = self.seats.get(msg.get("seat"))
        rid = msg.get("rid")
        cmd = msg.get("cmd")
        if seat is None:
            self.log(f"# Khong co ghe {msg.get('seat')}")
            self.send_json({"type": "ack", "seat": msg.get("seat"), "rid": rid, "ok": False})
            return

        if cmd == "warn":
            seat.warning = bool(msg.get("on"))
            self.log(f"# WARN {seat.name} {'ON' if seat.warning else 'OFF'}")
            self.send_json({"type": "ack", "seat": seat.name, "rid": rid, "ok": True})
        elif cmd == "ota":
            self.log(f"# OTA {seat.name}: gia lap tai firmware, khoi dong lai sau 3 giay")
            self.send_json({"type": "ack", "seat": seat.name, "rid": rid, "ok": True})
            threading.Thread(target=self.fake_ota, args=(seat,), daemon=True).start()
        else:
            self.log(f"# Lenh khong ho tro: {cmd}")
            self.send_json({"type": "ack", "seat": seat.name, "rid": rid, "ok": False})

    def fake_ota(self, seat):
        time.sleep(3)
        major, minor = seat.fw.split(".")
        seat.fw = f"{major}.{int(minor) + 1}"
        seat.seq = 0
        self.log(f"# {seat.name} da khoi dong lai voi fw {seat.fw}")
        self.send_hello(seat)

    def reader(self, conn):
        """Thread doc tung dong lenh tu gateway."""
        try:
            for raw in conn.makefile("r", encoding="utf-8", newline="\n"):
                line = raw.strip()
                if line:
                    print(f"<< {line}", flush=True)
                    self.handle_command(line)
        except OSError:
            pass

    # ---------- vong lap chinh ----------
    def update_states(self):
        t = self.sim_time()
        self.seats["Seat-01"].set_state(seat01_state_at(t), t)
        self.seats["Seat-02"].set_state(script_state_at(SEAT02_SCRIPT, t), t)
        self.seats["Seat-03"].set_state(script_state_at(SEAT03_SCRIPT, t), t)

    def serve_client(self, conn, addr):
        print(f"# Gateway da ket noi tu {addr}", flush=True)
        self.conn = conn
        threading.Thread(target=self.reader, args=(conn,), daemon=True).start()

        for seat in self.seats.values():
            self.send_hello(seat)

        real_period = PERIOD / self.speed
        while True:
            self.update_states()
            for seat in self.seats.values():
                if not self.send_telemetry(seat):
                    print("# Gateway da ngat ket noi, cho ket noi moi...", flush=True)
                    self.conn = None
                    return
            s1 = self.seats["Seat-01"]
            print(f"# t={self.sim_time():6.0f}s  Seat-01={s1.state:<11} obj_secs={s1.obj_secs(self.sim_time())}", flush=True)
            time.sleep(real_period)

    def run(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", self.port))
        server.listen(1)
        print(f"# Fake bridge dang cho o socket://localhost:{self.port} (speed x{self.speed})", flush=True)
        try:
            while True:
                conn, addr = server.accept()
                with conn:
                    self.serve_client(conn, addr)
        except KeyboardInterrupt:
            print("\n# Dung fake bridge.")
        finally:
            server.close()


def main():
    parser = argparse.ArgumentParser(description="Bridge gia lap cho gateway IoT")
    parser.add_argument("--port", type=int, default=7000)
    parser.add_argument("--speed", type=float, default=1.0,
                        help="he so tua nhanh thoi gian, vd 10 = nhanh gap 10 lan")
    args = parser.parse_args()
    FakeBridge(args.port, args.speed).run()


if __name__ == "__main__":
    main()