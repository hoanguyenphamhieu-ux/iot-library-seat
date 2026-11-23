// main.cpp - Firmware node ghe (vai A).
//
// Mot file nguon, 4 che do, chon bang env trong platformio.ini:
//   APP_MODE_HELLO   : in MAC, flash, PSRAM, phien ban core; chay thu LED 4 mau
//   APP_MODE_SENSORS : quet I2C, in radar + ToF 5 lan/giay de kiem tra va hieu chinh
//   APP_MODE_COLLECT : in 19 so CSV 10 lan/giay cho edge-impulse-data-forwarder (buoc A7)
//   (mac dinh)       : firmware day du - may trang thai + LED + ESP-NOW
#include <Arduino.h>
#include <esp_arduino_version.h>

#include "config.h"
#include "board_pins.h"
#include "seat_packet.h"
#include "sensors.h"
#include "status_led.h"

#if !defined(APP_MODE_HELLO) && !defined(APP_MODE_SENSORS) && !defined(APP_MODE_COLLECT)
#include "link.h"
#endif
#if defined(APP_MODE_HELLO)
#include <WiFi.h>
#endif

static void waitForSerial() {
  uint32_t t0 = millis();
  while (!Serial && millis() - t0 < 3000) delay(10);  // cho mo Serial Monitor toi da 3 giay
}

static const char *stateName(uint8_t s) {
  switch (s) {
    case ST_EMPTY:       return "EMPTY";
    case ST_OCCUPIED:    return "OCCUPIED";
    case ST_OBJECT_ONLY: return "OBJECT_ONLY";
    default:             return "?";
  }
}

// =====================================================================
#if defined(APP_MODE_HELLO)
// =====================================================================
void setup() {
  Serial.begin(115200);
  waitForSerial();
  WiFi.mode(WIFI_STA);
  Serial.println();
  Serial.println("===== YoloUNO HELLO =====");
  Serial.printf("MAC (chep vao secrets.h): %s\n", WiFi.macAddress().c_str());
  Serial.printf("Flash: %u byte (8 MB = 8388608, 4 MB = 4194304)\n", ESP.getFlashChipSize());
  Serial.printf("PSRAM: %u byte\n", ESP.getPsramSize());
  Serial.printf("Arduino core: %d.%d.%d\n", ESP_ARDUINO_VERSION_MAJOR, ESP_ARDUINO_VERSION_MINOR,
                ESP_ARDUINO_VERSION_PATCH);
  ledBegin();
}

void loop() {
  static const LedColor seq[] = {LedColor::Green, LedColor::Red, LedColor::Orange, LedColor::Yellow};
  static const char *names[] = {"xanh la (EMPTY)", "do (OCCUPIED)", "cam (OBJECT_ONLY)", "vang (canh bao)"};
  static uint8_t i = 0;
  ledShow(seq[i]);
  Serial.printf("LED: %s   |   MAC: %s\n", names[i], WiFi.macAddress().c_str());
  i = (i + 1) % 4;
  delay(1500);
}

// =====================================================================
#elif defined(APP_MODE_SENSORS)
// =====================================================================
void setup() {
  Serial.begin(115200);
  waitForSerial();
  Serial.println("\n===== KIEM TRA CAM BIEN =====");
  ledBegin();
  i2cScan();
  bool tof = tofBegin();
  bool rad = radarBegin();
  if (rad) radarApplyMaxGate(RADAR_MAX_GATE, RADAR_NO_ONE_WINDOW_S);
  Serial.printf("# radar=%s tof=%s\n", rad ? "OK" : "LOI", tof ? "OK" : "LOI");
}

void loop() {
  radarPoll();
  tofPoll();
  static uint32_t last = 0;
  if (millis() - last < 200) return;
  last = millis();

  const RadarFrame &r = radarFrame();
  uint16_t mm = tofMm();
  bool object = mm < TOF_OBJECT_MM;
  ledShow(r.presence ? LedColor::Red : (object ? LedColor::Orange : LedColor::Green));

  Serial.printf("radar[%s] pres=%d mov=%d sta=%d | tof=%4u mm %s | movE=",
                radarFresh() ? "ok " : "---", r.presence, r.moving, r.stationary, mm,
                object ? "(CO VAT)" : "        ");
  for (int g = 0; g < 9; g++) Serial.printf("%4u", r.moveE[g]);
  Serial.print(" | staE=");
  for (int g = 0; g < 9; g++) Serial.printf("%4u", r.stillE[g]);
  Serial.println();
}

// =====================================================================
#elif defined(APP_MODE_COLLECT)
// =====================================================================
// Chi in dong so lieu, KHONG in gi khac, de edge-impulse-data-forwarder doc duoc.
void setup() {
  Serial.begin(115200);
  waitForSerial();
  ledBegin();
  tofBegin();
  if (radarBegin()) radarApplyMaxGate(RADAR_MAX_GATE, RADAR_NO_ONE_WINDOW_S);
  ledShow(LedColor::Blue);
}

void loop() {
  radarPoll();
  tofPoll();
  static uint32_t last = 0;
  if (millis() - last < SAMPLE_PERIOD_MS) return;
  last = millis();
  const RadarFrame &r = radarFrame();
  for (int g = 0; g < 9; g++) Serial.printf("%u,", r.moveE[g]);
  for (int g = 0; g < 9; g++) Serial.printf("%u,", r.stillE[g]);
  Serial.printf("%u\n", tofMm());
}

// =====================================================================
#else  // FIRMWARE DAY DU
// =====================================================================
static uint16_t seq = 0;
static uint8_t acceptedState = ST_EMPTY;   // trang thai da qua chong nhieu
static uint8_t candidateState = ST_EMPTY;  // trang thai vua tinh, dang cho du 3 giay
static uint32_t candidateSince = 0;
static uint32_t objectSince = 0;           // thoi diem vao OBJECT_ONLY
static uint8_t aiLabel = AI_EMPTY;
static uint8_t aiConf = 0;
static bool warning = false;               // dang bi canh bao (nhan CMD_WARN on)
static uint32_t lastSendMs = 0;

static uint16_t objSecs() {
  if (acceptedState != ST_OBJECT_ONLY) return 0;
  uint32_t s = (millis() - objectSince) / 1000;
  return s > 65535 ? 65535 : (uint16_t)s;
}

static LedColor colorFor(uint8_t state) {
  switch (state) {
    case ST_OCCUPIED:    return LedColor::Red;
    case ST_OBJECT_ONLY: return LedColor::Orange;
    default:             return LedColor::Green;
  }
}

// Quyet dinh trang thai tuc thoi tu cam bien.
// Hien tai dung luat tren radar + ToF. Khi co model TinyML (buoc A7),
// thay phan tinh aiLabel/aiConf bang ket qua run_classifier().
static uint8_t decideRawState() {
  const RadarFrame &r = radarFrame();
  bool radarOk = radarFresh();
  bool object = tofMm() < TOF_OBJECT_MM;

  if (radarOk && r.moving)          { aiLabel = AI_PERSON_MOVE;  }
  else if (radarOk && r.stationary) { aiLabel = AI_PERSON_STILL; }
  else if (object)                  { aiLabel = AI_BAG;          }
  else                              { aiLabel = AI_EMPTY;        }
  aiConf = 0;  // 0 = dang dung luat, chua co TinyML

  bool person = radarOk && r.presence;
  if (person) return ST_OCCUPIED;
  if (object) return ST_OBJECT_ONLY;
  return ST_EMPTY;
}

static void sendPacket(uint8_t type) {
  SeatPacket p = {};
  p.type = type;
  p.seat_id = SEAT_ID;
  p.seq = ++seq;
  p.state = acceptedState;
  p.ai_label = aiLabel;
  p.ai_conf = aiConf;
  p.tof_mm = tofMm();
  p.obj_secs = objSecs();
  p.fw_major = FW_VERSION_MAJOR;
  p.fw_minor = FW_VERSION_MINOR;
  linkSend(&p, sizeof(p));
  lastSendMs = millis();
  Serial.printf("# TX %s seq=%u state=%s ai=%u tof=%u obj_secs=%u\n",
                type == MSG_HELLO ? "HELLO" : "TELEM", p.seq, stateName(p.state), p.ai_label,
                p.tof_mm, p.obj_secs);
}

static void sendAck(const CmdPacket &cmd, bool ok) {
  CmdPacket ack = cmd;
  ack.type = MSG_ACK;
  ack.ok = ok ? 1 : 0;
  linkSend(&ack, sizeof(ack));
}

static void handleCommands() {
  CmdPacket cmd;
  while (linkPopCmd(cmd)) {
    if (cmd.cmd == CMD_WARN) {
      warning = cmd.arg != 0;
      Serial.printf("# RX WARN %s (rid=%u)\n", warning ? "ON" : "OFF", cmd.rid);
      sendAck(cmd, true);
    } else if (cmd.cmd == CMD_OTA) {
      Serial.printf("# RX OTA (rid=%u): chua ho tro, se lam o buoc A6\n", cmd.rid);
      sendAck(cmd, false);
    } else {
      sendAck(cmd, false);
    }
  }
}

void setup() {
  Serial.begin(115200);
  waitForSerial();
  Serial.printf("\n===== NODE GHE Seat-%02d, fw %d.%d =====\n", SEAT_ID, FW_VERSION_MAJOR,
                FW_VERSION_MINOR);
  ledBegin();
  ledShow(LedColor::White);  // dang khoi dong

  bool tof = tofBegin();
  bool rad = radarBegin();
  if (rad) radarApplyMaxGate(RADAR_MAX_GATE, RADAR_NO_ONE_WINDOW_S);
  bool link = linkBegin();
  if (!tof || !rad || !link) {
    Serial.println("# CANH BAO: co thanh phan loi, xem cac dong [..] o tren");
    ledShow(LedColor::Purple);  // tim = co loi khi khoi dong
    delay(2000);
  }
  candidateSince = millis();
  sendPacket(MSG_HELLO);
}

void loop() {
  radarPoll();
  tofPoll();
  handleCommands();

  uint32_t now = millis();

  // ---- quyet dinh trang thai 2 lan/giay, co chong nhieu 3 giay ----
  static uint32_t lastDecide = 0;
  if (now - lastDecide >= DECIDE_PERIOD_MS) {
    lastDecide = now;
    uint8_t raw = decideRawState();
    if (raw != candidateState) {
      candidateState = raw;
      candidateSince = now;
    }
    if (candidateState != acceptedState && now - candidateSince >= DEBOUNCE_MS) {
      Serial.printf("# STATE %s -> %s\n", stateName(acceptedState), stateName(candidateState));
      acceptedState = candidateState;
      if (acceptedState == ST_OBJECT_ONLY) objectSince = now;
      else warning = false;  // nguoi quay lai hoac ghe trong: tu tat canh bao, khong cho lenh OFF
      sendPacket(MSG_TELEMETRY);  // gui ngay khi doi trang thai
    }
  }

  // ---- heartbeat ----
  if (now - lastSendMs >= HEARTBEAT_MS) sendPacket(MSG_TELEMETRY);

  // ---- LED ----
  ledUpdate(colorFor(acceptedState), warning);
}
#endif
