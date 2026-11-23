// main.cpp - Firmware node bridge (vai A).
// ESP-NOW (tu cac node ghe) <-> USB Serial (toi gateway Python), dinh dang CONTRACT.md muc 3.3.
//
// Quy uoc Serial: moi dong la 1 JSON; dong bat dau bang '#' la log, gateway bo qua.
// Che do hello: build env "hello" de in MAC cua bridge (chep vao BRIDGE_MAC trong secrets.h).
#include <Arduino.h>
#include <WiFi.h>
#include <esp_arduino_version.h>
#include <esp_now.h>
#include <esp_wifi.h>

#include "board_pins.h"
#include "seat_packet.h"
#include "secrets.h"

#if LED_PIN >= 0
#include <Adafruit_NeoPixel.h>
static Adafruit_NeoPixel led(1, LED_PIN, NEO_GRB + NEO_KHZ800);
#endif

#define ESPNOW_CHANNEL 1
#define MAX_SEATS 3

// ---------------- hang doi tu callback ESP-NOW ----------------
struct RxItem {
  uint8_t mac[6];
  int8_t rssi;
  uint8_t len;
  uint8_t data[32];
};
static QueueHandle_t rxQueue = nullptr;

// ---------------- bang seat_id -> MAC ----------------
static uint8_t seatMac[MAX_SEATS + 1][6];
static bool seatKnown[MAX_SEATS + 1] = {false};
static char fwOf[MAX_SEATS + 1][8];

static void blink(uint8_t r, uint8_t g, uint8_t b) {
#if LED_PIN >= 0
  led.setPixelColor(0, led.Color(r, g, b));
  led.show();
#else
  (void)r; (void)g; (void)b;
#endif
}
#if ESP_ARDUINO_VERSION_MAJOR < 3
// Core 2.x: callback ESP-NOW khong co RSSI -> bat promiscuous, doc RSSI cua frame ESP-NOW
// (action frame 0xD0, category 0x7F, OUI Espressif 18:FE:34). Callback nay chay ngay truoc onRecv.
static volatile int8_t lastRssi = 0;
static uint8_t lastRssiMac[6];
static void onPromisc(void *buf, wifi_promiscuous_pkt_type_t type) {
  if (type != WIFI_PKT_MGMT) return;
  const wifi_promiscuous_pkt_t *pkt = (const wifi_promiscuous_pkt_t *)buf;
  const uint8_t *p = pkt->payload;
  if (pkt->rx_ctrl.sig_len < 28) return;
  if (p[0] != 0xD0 || p[24] != 0x7F || p[25] != 0x18 || p[26] != 0xFE || p[27] != 0x34) return;
  memcpy(lastRssiMac, p + 10, 6);  // dia chi nguoi gui (addr2)
  lastRssi = pkt->rx_ctrl.rssi;
}
#endif
#if ESP_ARDUINO_VERSION_MAJOR >= 3
static void onRecv(const esp_now_recv_info_t *info, const uint8_t *data, int len) {
  RxItem it = {};
  memcpy(it.mac, info->src_addr, 6);
  it.rssi = info->rx_ctrl ? info->rx_ctrl->rssi : 0;
#else
static void onRecv(const uint8_t *mac, const uint8_t *data, int len) {
  RxItem it = {};
  memcpy(it.mac, mac, 6);
  it.rssi = (memcmp(mac, lastRssiMac, 6) == 0) ? lastRssi : 0;
#endif
  if (len <= 0 || len > (int)sizeof(it.data)) return;
  it.len = (uint8_t)len;
  memcpy(it.data, data, len);
  xQueueSend(rxQueue, &it, 0);  // chi copy vao hang doi, KHONG Serial.print o day
}

static bool addPeer(const uint8_t mac[6]) {
  if (esp_now_is_peer_exist(mac)) return true;
  esp_now_peer_info_t peer = {};
  memcpy(peer.peer_addr, mac, 6);
  peer.channel = ESPNOW_CHANNEL;
  peer.ifidx = WIFI_IF_STA;
#if USE_ESPNOW_ENCRYPTION
  peer.encrypt = true;
  memcpy(peer.lmk, ESPNOW_LMK, 16);
#else
  peer.encrypt = false;
#endif
  return esp_now_add_peer(&peer) == ESP_OK;
}

static const char *stateName(uint8_t s) {
  switch (s) {
    case ST_EMPTY:       return "EMPTY";
    case ST_OCCUPIED:    return "OCCUPIED";
    case ST_OBJECT_ONLY: return "OBJECT_ONLY";
    default:             return "UNKNOWN";
  }
}

static const char *aiName(uint8_t a) {
  switch (a) {
    case AI_EMPTY:        return "empty";
    case AI_PERSON_STILL: return "person_still";
    case AI_PERSON_MOVE:  return "person_move";
    case AI_BAG:          return "bag";
    default:              return "unknown";
  }
}

// ---------------- ESP-NOW -> Serial ----------------
static void handleRx(const RxItem &it) {
  uint8_t type = it.data[0];

  if ((type == MSG_HELLO || type == MSG_TELEMETRY) && it.len == sizeof(SeatPacket)) {
    SeatPacket p;
    memcpy(&p, it.data, sizeof(p));
    if (p.seat_id < 1 || p.seat_id > MAX_SEATS) {
      Serial.printf("# seat_id khong hop le: %u\n", p.seat_id);
      return;
    }
    if (!seatKnown[p.seat_id] || memcmp(seatMac[p.seat_id], it.mac, 6) != 0) {
      memcpy(seatMac[p.seat_id], it.mac, 6);
      seatKnown[p.seat_id] = true;
      addPeer(it.mac);
      Serial.printf("# Seat-%02u co MAC %02X:%02X:%02X:%02X:%02X:%02X\n", p.seat_id, it.mac[0],
                    it.mac[1], it.mac[2], it.mac[3], it.mac[4], it.mac[5]);
    }
    snprintf(fwOf[p.seat_id], sizeof(fwOf[0]), "%u.%u", p.fw_major, p.fw_minor);

    if (type == MSG_HELLO) {
      Serial.printf("{\"type\":\"hello\",\"seat\":\"Seat-%02u\",\"fw\":\"%s\"}\n", p.seat_id,
                    fwOf[p.seat_id]);
    } else {
      Serial.printf(
          "{\"type\":\"telemetry\",\"seat\":\"Seat-%02u\",\"seq\":%u,\"state\":\"%s\",\"ai\":\"%s\","
          "\"conf\":%u,\"tof\":%u,\"obj_secs\":%u,\"rssi\":%d,\"fw\":\"%s\"}\n",
          p.seat_id, p.seq, stateName(p.state), aiName(p.ai_label), p.ai_conf, p.tof_mm,
          p.obj_secs, it.rssi, fwOf[p.seat_id]);
    }
    blink(0, 0, 60);
    return;
  }

  if (type == MSG_ACK && it.len == sizeof(CmdPacket)) {
    CmdPacket a;
    memcpy(&a, it.data, sizeof(a));
    Serial.printf("{\"type\":\"ack\",\"seat\":\"Seat-%02u\",\"rid\":%u,\"ok\":%s}\n", a.seat_id,
                  a.rid, a.ok ? "true" : "false");
    return;
  }

  Serial.printf("# Goi la: type=%u len=%u\n", type, it.len);
}

// ---------------- Serial -> ESP-NOW ----------------
// Doc gia tri chuoi cua "key" trong 1 dong JSON phang. Tra ve false neu khong co.
static bool jsonStr(const char *line, const char *key, char *out, size_t outLen) {
  char pat[24];
  snprintf(pat, sizeof(pat), "\"%s\":\"", key);
  const char *p = strstr(line, pat);
  if (!p) return false;
  p += strlen(pat);
  size_t n = 0;
  while (*p && *p != '"' && n + 1 < outLen) out[n++] = *p++;
  out[n] = '\0';
  return true;
}

// Doc gia tri so (hoac true/false) cua "key" trong 1 dong JSON phang.
static bool jsonInt(const char *line, const char *key, long &out) {
  char pat[24];
  snprintf(pat, sizeof(pat), "\"%s\":", key);
  const char *p = strstr(line, pat);
  if (!p) return false;
  p += strlen(pat);
  while (*p == ' ') p++;
  if (strncmp(p, "true", 4) == 0) { out = 1; return true; }
  if (strncmp(p, "false", 5) == 0) { out = 0; return true; }
  char *end = nullptr;
  out = strtol(p, &end, 10);
  return end != p;
}

static void replyAckFail(uint8_t seatId, long rid) {
  Serial.printf("{\"type\":\"ack\",\"seat\":\"Seat-%02u\",\"rid\":%ld,\"ok\":false}\n", seatId, rid);
}

static void handleLine(const char *line) {
  char type[12], seat[12], cmd[12];
  if (!jsonStr(line, "type", type, sizeof(type)) || strcmp(type, "cmd") != 0) {
    Serial.printf("# Bo qua dong: %s\n", line);
    return;
  }
  if (!jsonStr(line, "seat", seat, sizeof(seat)) || !jsonStr(line, "cmd", cmd, sizeof(cmd))) {
    Serial.println("# Lenh thieu seat hoac cmd");
    return;
  }
  long rid = 0, on = 0;
  jsonInt(line, "rid", rid);
  jsonInt(line, "on", on);

  const char *dash = strrchr(seat, '-');
  long seatId = dash ? strtol(dash + 1, nullptr, 10) : 0;  // "Seat-01" -> 1
  if (seatId < 1 || seatId > MAX_SEATS || !seatKnown[seatId]) {
    Serial.printf("# Chua biet MAC cua %s (ghe chua gui goi nao)\n", seat);
    replyAckFail((uint8_t)seatId, rid);
    return;
  }

  CmdPacket c = {};
  c.type = MSG_CMD;
  c.seat_id = (uint8_t)seatId;
  c.rid = (uint16_t)rid;
  if (strcmp(cmd, "warn") == 0) {
    c.cmd = CMD_WARN;
    c.arg = on ? 1 : 0;
  } else if (strcmp(cmd, "ota") == 0) {
    c.cmd = CMD_OTA;
  } else {
    Serial.printf("# Lenh khong ho tro: %s\n", cmd);
    replyAckFail((uint8_t)seatId, rid);
    return;
  }

  esp_err_t err = esp_now_send(seatMac[seatId], (const uint8_t *)&c, sizeof(c));
  if (err != ESP_OK) {
    Serial.printf("# Gui lenh loi: %s\n", esp_err_to_name(err));
    replyAckFail((uint8_t)seatId, rid);
  } else {
    Serial.printf("# Da gui %s toi %s (rid=%ld)\n", cmd, seat, rid);
  }
}

static void pollSerial() {
  static char buf[200];
  static size_t n = 0;
  while (Serial.available()) {
    char ch = (char)Serial.read();
    if (ch == '\r') continue;
    if (ch == '\n') {
      buf[n] = '\0';
      if (n > 0) handleLine(buf);
      n = 0;
    } else if (n + 1 < sizeof(buf)) {
      buf[n++] = ch;
    } else {
      n = 0;  // dong qua dai, bo
      Serial.println("# Dong qua dai, bo qua");
    }
  }
}

// =====================================================================
void setup() {
  Serial.begin(115200);
  uint32_t t0 = millis();
  while (!Serial && millis() - t0 < 3000) delay(10);

#if LED_PIN >= 0
  led.begin();
  led.setBrightness(40);
#endif

  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  esp_wifi_set_channel(ESPNOW_CHANNEL, WIFI_SECOND_CHAN_NONE);
  Serial.printf("# BRIDGE MAC: %s (chep vao BRIDGE_MAC trong secrets.h)\n",
                WiFi.macAddress().c_str());

#if defined(APP_MODE_HELLO)
  Serial.printf("# Flash: %u byte, core %d.%d.%d\n", ESP.getFlashChipSize(),
                ESP_ARDUINO_VERSION_MAJOR, ESP_ARDUINO_VERSION_MINOR, ESP_ARDUINO_VERSION_PATCH);
  return;
#endif

  rxQueue = xQueueCreate(16, sizeof(RxItem));
  if (esp_now_init() != ESP_OK) {
    Serial.println("# esp_now_init that bai");
    blink(80, 0, 0);
    return;
  }
#if USE_ESPNOW_ENCRYPTION
  esp_now_set_pmk(ESPNOW_PMK);
  // Ma hoa: phai them truoc cac node co ten trong NODE_MACS, neu khong se khong giai ma duoc
  for (size_t i = 0; i < sizeof(NODE_MACS) / sizeof(NODE_MACS[0]); i++) {
    addPeer(NODE_MACS[i]);
  }
#endif
  esp_now_register_recv_cb(onRecv);
  #if ESP_ARDUINO_VERSION_MAJOR < 3
  wifi_promiscuous_filter_t filt = {};
  filt.filter_mask = WIFI_PROMIS_FILTER_MASK_MGMT;
  esp_wifi_set_promiscuous_filter(&filt);
  esp_wifi_set_promiscuous_rx_cb(onPromisc);
  esp_wifi_set_promiscuous(true);
#endif
  Serial.printf("# Bridge san sang, kenh %d, ma hoa %s\n", ESPNOW_CHANNEL,
                USE_ESPNOW_ENCRYPTION ? "BAT" : "TAT");
  blink(0, 40, 0);
}

void loop() {
#if defined(APP_MODE_HELLO)
  static uint32_t last = 0;
  if (millis() - last > 2000) {
    last = millis();
    Serial.printf("# BRIDGE MAC: %s\n", WiFi.macAddress().c_str());
  }
  return;
#endif
static uint32_t lastAlive = 0;  // nhip "con song" de biet bridge dang chay
if (millis() - lastAlive > 5000) {
  lastAlive = millis();
  Serial.printf("# bridge alive, MAC %s\n", WiFi.macAddress().c_str());
}
  RxItem it;
  while (rxQueue && xQueueReceive(rxQueue, &it, 0) == pdTRUE) handleRx(it);
  pollSerial();

  static uint32_t lastOff = 0;  // tat den nhay sau 50 ms
  if (millis() - lastOff > 50) {
    lastOff = millis();
    blink(0, 10, 0);
  }
}
