"""Doc/ghi tung dong JSON voi node bridge (CONTRACT muc 3.3).

Dung serial.serial_for_url nen mo duoc ca:
  - cong that:      COM5
  - bridge gia lap: socket://localhost:7000
"""
#chỉ làm việc với bridge, mở cổng, đọc từng dòng, đổi thành dict Python, và ghi lệnh xuống
import json
import logging
import time

import serial

log = logging.getLogger("serial") #tạo logger tên serial


class SerialLink:
    #hàm init lưu thông số, chưa mở kết nối port=none
    def __init__(self, url, baudrate=115200):
        self.url = url
        self.baudrate = baudrate
        self.port = None
    #mở kết nối
    def _open(self):
        while self.port is None:
            try:
                #đọc chuỗi url xem là cổng COM5 thật hay socket tới bridge giả
                self.port = serial.serial_for_url(self.url, baudrate=self.baudrate, timeout=1)
                log.info("Da mo %s", self.url)
                # mở không được (bridge giả chưa chạy, cổng COM 
                # đang bị chương trình khác giữ, rút cáp) thì ghi cảnh báo, chờ 3 giây rồi thử lại
            except (serial.SerialException, OSError) as e:
                log.warning("Chua mo duoc %s (%s), thu lai sau 3 giay...", self.url, e)
                time.sleep(3)

    def _close(self):
        try:
            # đóng cổng, bỏ qua mọi lỗi khi đóng
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
                raw = self.port.readline() #đọc bytes cho đến khi gặp ký tự xuống dòng \n, hoặc hết 1 giây timeout
                #lỗi thì in thông báo và dừng ctrinh
            except (serial.SerialException, OSError) as e: # rút cáp->ném lỗi -> đóng cổng, mở lại ở lần lặp kế tiếp
                log.warning("Mat ket noi Serial (%s), mo lai...", e)
                self._close()
                continue

            if not raw: # qua một giây mà chưa có data
                if getattr(self.port, "is_open", True) is False: # bên socket đóng kết nối cũng tính là rỗng->phải check
                    self._close()
                yield None #mỗi giây, vòng for nhận none và chạy một lượt kể cả khi bridge im lặng
                continue

            line = raw.decode("utf-8", errors="replace").strip() #đổi bytes thành chuỗi, thay byte rác thành ? thay vì crash ctrinh
            if not line: #dòng rỗng thì bỏ qua, ko yield
                continue
            if line.startswith("#"):# dòng bắt đầu bằng # thì là debug->ghi vô debug rồi bỏ qua
                log.debug("bridge: %s", line) 
                continue
            try:
                yield json.loads(line) # đổi chuỗi thành dict rồi yield đưa dict cho main.py
            except json.JSONDecodeError:# dòng hỏng thì cảnh báo và bỏ qua, ko crash ctrinh
                log.warning("Bo qua dong khong phai JSON: %r", line)

    def write_json(self, obj):
        if self.port is None:
            log.warning("Chua co ket noi Serial, khong gui duoc: %s", obj)
            return False
        #tạo JSON gọn, không có dấu cách thừa, xong đổi chuỗi sang byte
        data = (json.dumps(obj, separators=(",", ":")) + "\n").encode("utf-8")
        try:
            self.port.write(data) #write chỉ nhận byte
            return True
        except (serial.SerialException, OSError) as e:
            log.warning("Ghi Serial loi (%s)", e)
            self._close()
            return False