"""Ket noi MQTT toi CoreIOT theo Gateway MQTT API cua ThingsBoard.

Mot ket noi duy nhat bang access token cua device Library-Gateway,
dai dien cho nhieu device con (Seat-01..03, Room-A).
  v1/gateway/connect    : khai bao device con
  v1/gateway/telemetry  : gui telemetry cho device con
  v1/gateway/rpc        : nhan lenh tu server (dung o buoc B4)
"""
#chỉ làm việc với CoreIOT. Giữ kết nối MQTT, gửi telemetry, nhận lệnh RPC
# outbox: mất mạng thì telemetry được cất vào store và flush_outbox() gửi bù khi có mạng.
import json     #đổi đổi dict thành chuỗi JSON và ngược lại
import logging
import time

import paho.mqtt.client as mqtt     #thư viện MQTT cho Python

log = logging.getLogger("tb")


def now_ms():
    return int(time.time() * 1000) #trả số giây từ năm 1970 (có phần thập phân)


class TBGateway:
    def __init__(self, host, port, token, store=None):
        self.store = store         # B5: Store de luu ban tin khi mat mang (None = khong dung outbox)
        self.host = host            #địa chỉ và port của CoreIOT (app.coreiot.io, 1883)
        self.port = port
        self.devices = {}          # ten device -> profile, de khai bao lai khi ket noi lai
        self.on_rpc = None         # B4 se gan ham xu ly vao day

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)   # khởi tạo một client, chọn kiểu viết hàm callback mới, paho-mqtt 2.x
        self.client.username_pw_set(token)                           # đặt username = access token của Library-Gateway
        self.client.reconnect_delay_set(min_delay=1, max_delay=30) #sau khi rớt mạng, thử nối lại sau 1 giây, nếu chưa được thì chờ lâu dần, tối đa 30 giây
        self.client.on_connect = self._on_connect   #gán callback
        self.client.on_disconnect = self._on_disconnect #gán callback
        self.client.on_message = self._on_message   #gán callback

    # ket noi
    def start(self):
        log.info("Dang ket noi MQTT %s:%s ...", self.host, self.port)
        self.client.connect_async(self.host, self.port, keepalive=60) #không block cpu trong lúc chờ client kết nối tới máy chủ
        self.client.loop_start()   # tạo một luồng chạy nền làm toàn bộ việc mạng: quay số, nghe tin, gửi tín hiệu “tôi còn sống” 
                                    # mỗi 60 giây (keepalive), tự nối lại khi rớt.

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()

    def is_connected(self):
        return self.client.is_connected()

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure: #kết quả fail ? error: "đã kết nối"
            log.error("CoreIOT tu choi ket noi: %s (sai token? sai host?)", reason_code)
            return
        log.info("Da ket noi CoreIOT")
        client.subscribe("v1/gateway/rpc", qos=1) #kết nối rồi thì subscribe nghe kênh lệnh, làm lại mỗi lần sau khi rớt mạng
        for name, profile in self.devices.items():   # khai báo lại device con sau khi rớt mạng
            self._publish("v1/gateway/connect", {"device": name, "type": profile})

    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        log.warning("Mat ket noi CoreIOT (%s), paho se tu ket noi lai", reason_code)
    #khi có tin tới, chuyển mess dạng byte thành dict rồi 
    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            log.warning("Bo qua ban tin MQTT loi tren %s", msg.topic)
            return
        if msg.topic == "v1/gateway/rpc":
            log.info("Nhan RPC: %s", payload) #kênh RPC thì log, rồi gọi self.on_rpc(...) nếu ổ cắm đã được cắm hàm.
            if self.on_rpc:
                self.on_rpc(payload)

    # gửi
    def _publish(self, topic, obj):
        payload = json.dumps(obj, separators=(",", ":"))
        # B5: dang mat ket noi -> cat telemetry vao outbox (SQLite), khi co mang flush_outbox() se gui bu
        if self.store is not None and topic == "v1/gateway/telemetry" and not self.client.is_connected():
            self.store.outbox_add(topic, payload)
            return False
        info = self.client.publish(topic, payload, qos=1)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            log.warning("Chua gui duoc len %s (rc=%s) - chua ket noi?", topic, info.rc)
            return False
        return True

    def flush_outbox(self, limit=100):
        """B5: gui bu cac ban tin da luu luc mat mang (giu nguyen ts goc). Tra ve so ban tin da gui."""
        if self.store is None or not self.client.is_connected():
            return 0
        rows = self.store.outbox_take(limit)
        sent = []
        for row_id, topic, payload in rows:
            info = self.client.publish(topic, payload, qos=1)
            if info.rc != mqtt.MQTT_ERR_SUCCESS:
                break                                  # rot mang giua chung -> de lan sau
            sent.append(row_id)
        self.store.outbox_delete(sent)
        if sent:
            log.info("Gui bu %d ban tin (con %d trong outbox)", len(sent), self.store.outbox_count())
        return len(sent)

    # ghi vào sổ, rồi gửi tin {"device":"Seat-01","type":"library-seat"} lên kênh v1/gateway/connect
    def connect_device(self, name, profile):
        self.devices[name] = profile
        log.info("Khai bao device %s (profile %s)", name, profile)
        return self._publish("v1/gateway/connect", {"device": name, "type": profile})

    def send_telemetry(self, name, values, ts=None):
        #tạo cấu trúc mà Gateway API yêu cầu
        payload = {name: [{"ts": ts or now_ms(), "values": values}]}
        return self._publish("v1/gateway/telemetry", payload)
    #trả lời lệnh, publish kết quả lên v1/gateway/rpc dạng
    def send_rpc_reply(self, device, rpc_id, data):
        """Tra loi RPC: {"device":..., "id":..., "data":{"success":true}}"""
        return self._publish("v1/gateway/rpc", {"device": device, "id": rpc_id, "data": data})