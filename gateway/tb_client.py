"""Ket noi MQTT toi CoreIOT theo Gateway MQTT API cua ThingsBoard.

Mot ket noi duy nhat bang access token cua device Library-Gateway,
dai dien cho nhieu device con (Seat-01..03, Room-A).
  v1/gateway/connect    : khai bao device con
  v1/gateway/telemetry  : gui telemetry cho device con
  v1/gateway/rpc        : nhan lenh tu server (dung o buoc B4)
"""
import json
import logging
import time

import paho.mqtt.client as mqtt

log = logging.getLogger("tb")


def now_ms():
    return int(time.time() * 1000)


class TBGateway:
    def __init__(self, host, port, token):
        self.host = host
        self.port = port
        self.devices = {}          # ten device -> profile, de khai bao lai khi ket noi lai
        self.on_rpc = None         # B4 se gan ham xu ly vao day

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)   # paho-mqtt 2.x
        self.client.username_pw_set(token)                           # username = access token
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

    # ---------- ket noi ----------
    def start(self):
        log.info("Dang ket noi MQTT %s:%s ...", self.host, self.port)
        self.client.connect_async(self.host, self.port, keepalive=60)
        self.client.loop_start()   # chay nen, tu ket noi lai khi rot mang

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()

    def is_connected(self):
        return self.client.is_connected()

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            log.error("CoreIOT tu choi ket noi: %s (sai token? sai host?)", reason_code)
            return
        log.info("Da ket noi CoreIOT")
        client.subscribe("v1/gateway/rpc", qos=1)
        for name, profile in self.devices.items():   # khai bao lai device con sau khi rot mang
            self._publish("v1/gateway/connect", {"device": name, "type": profile})

    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        log.warning("Mat ket noi CoreIOT (%s), paho se tu ket noi lai", reason_code)

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            log.warning("Bo qua ban tin MQTT loi tren %s", msg.topic)
            return
        if msg.topic == "v1/gateway/rpc":
            log.info("Nhan RPC: %s", payload)
            if self.on_rpc:
                self.on_rpc(payload)

    # ---------- gui ----------
    def _publish(self, topic, obj):
        info = self.client.publish(topic, json.dumps(obj, separators=(",", ":")), qos=1)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            log.warning("Chua gui duoc len %s (rc=%s) - chua ket noi?", topic, info.rc)
            return False
        return True

    def connect_device(self, name, profile):
        self.devices[name] = profile
        log.info("Khai bao device %s (profile %s)", name, profile)
        return self._publish("v1/gateway/connect", {"device": name, "type": profile})

    def send_telemetry(self, name, values, ts=None):
        payload = {name: [{"ts": ts or now_ms(), "values": values}]}
        return self._publish("v1/gateway/telemetry", payload)