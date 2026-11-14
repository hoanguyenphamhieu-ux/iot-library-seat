"""Doc/ghi tung dong JSON voi node bridge (CONTRACT muc 3.3).

Dung serial.serial_for_url nen mo duoc ca:
  - cong that:      COM5
  - bridge gia lap: socket://localhost:7000
"""
import json
import logging
import time

import serial

log = logging.getLogger("serial")


class SerialLink:
    def __init__(self, url, baudrate=115200):
        self.url = url
        self.baudrate = baudrate
        self.port = None

    def _open(self):
        while self.port is None:
            try:
                self.port = serial.serial_for_url(self.url, baudrate=self.baudrate, timeout=1)
                log.info("Da mo %s", self.url)
            except (serial.SerialException, OSError) as e:
                log.warning("Chua mo duoc %s (%s), thu lai sau 3 giay...", self.url, e)
                time.sleep(3)

    def _close(self):
        try:
            if self.port is not None:
                self.port.close()
        except Exception:
            pass
        self.port = None

    def messages(self):
        """Generator: tra ve dict cho moi dong JSON hop le.
        Tra ve None moi ~1 giay khi khong co du lieu, de vong lap chinh
        con lam duoc viec dinh ky (vd tinh loss_pct)."""
        while True:
            self._open()
            try:
                raw = self.port.readline()
            except (serial.SerialException, OSError) as e:
                log.warning("Mat ket noi Serial (%s), mo lai...", e)
                self._close()
                continue

            if not raw:
                # pyserial voi socket:// tra ve b"" khi het timeout HOAC khi ben kia dong ket noi.
                if getattr(self.port, "is_open", True) is False:
                    self._close()
                yield None
                continue

            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            if line.startswith("#"):
                log.debug("bridge: %s", line)   # dong log cua bridge, bo qua
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                log.warning("Bo qua dong khong phai JSON: %r", line)

    def write_json(self, obj):
        if self.port is None:
            log.warning("Chua co ket noi Serial, khong gui duoc: %s", obj)
            return False
        data = (json.dumps(obj, separators=(",", ":")) + "\n").encode("utf-8")
        try:
            self.port.write(data)
            return True
        except (serial.SerialException, OSError) as e:
            log.warning("Ghi Serial loi (%s)", e)
            self._close()
            return False