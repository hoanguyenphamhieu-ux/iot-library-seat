#include "sensors.h"

#include <Adafruit_VL53L0X.h>
#include <MyLD2410.h>
#include <Wire.h>

#include "board_pins.h"
#include "config.h"

// ======================= Radar LD2410C =======================
static MyLD2410 radar(Serial1);
static RadarFrame frame;
static bool radarStarted = false;

bool radarBegin() {
  if (RADAR_RX_PIN < 0 || RADAR_TX_PIN < 0) {
    Serial.println("# [RADAR] Chua dien RADAR_RX_PIN/RADAR_TX_PIN trong board_pins.h");
    return false;
  }
  Serial1.begin(256000, SERIAL_8N1, RADAR_RX_PIN, RADAR_TX_PIN);  // LD2410 mac dinh 256000 baud
  if (!radar.begin()) {
    Serial.println("# [RADAR] radar.begin() that bai: kiem tra nguon 5V, dao TX/RX, baud 256000");
    return false;
  }
  if (!radar.enhancedMode(true)) {
    Serial.println("# [RADAR] Khong bat duoc engineering (enhanced) mode, van chay basic mode");
  }
  radarStarted = true;
  Serial.printf("# [RADAR] OK, firmware radar: %s\n", radar.getFirmware().c_str());
  return true;
}

bool radarApplyMaxGate(uint8_t gate, uint8_t noOneWindowS) {
  if (!radarStarted) return false;
  bool ok = radar.setMaxGate(gate, gate, noOneWindowS);
  // setMaxGate co the dua radar ve basic mode, nen bat lai engineering mode
  radar.enhancedMode(true);
  Serial.printf("# [RADAR] setMaxGate(%u) %s\n", gate, ok ? "OK" : "THAT BAI");
  return ok;
}

static void copyGates(const MyLD2410::ValuesArray &src, uint8_t dst[9]) {
  for (int i = 0; i < 9; i++) {
    dst[i] = (i <= src.N) ? src.values[i] : 0;
  }
}

void radarPoll() {
  if (!radarStarted) return;
  if (radar.check() == MyLD2410::Response::DATA) {
    frame.valid = true;
    frame.presence = radar.presenceDetected();
    frame.moving = radar.movingTargetDetected();
    frame.stationary = radar.stationaryTargetDetected();
    if (radar.inEnhancedMode()) {
      copyGates(radar.getMovingSignals(), frame.moveE);
      copyGates(radar.getStationarySignals(), frame.stillE);
    }
    frame.lastMs = millis();
  }
}

const RadarFrame &radarFrame() { return frame; }

bool radarFresh(uint32_t maxAgeMs) {
  return frame.valid && (millis() - frame.lastMs) <= maxAgeMs;
}

// ======================= ToF VL53L0X =======================
static Adafruit_VL53L0X lox;
static bool tofStarted = false;
static uint16_t lastMm = TOF_FAR_MM;

static bool wireStarted() {
  static bool started = false;
  if (started) return true;
  if (I2C_SDA_PIN < 0 || I2C_SCL_PIN < 0) {
    Serial.println("# [I2C] Chua dien I2C_SDA_PIN/I2C_SCL_PIN trong board_pins.h");
    return false;
  }
  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);
  started = true;
  return true;
}

bool tofBegin() {
  if (!wireStarted()) return false;
  if (!lox.begin(VL53L0X_I2C_ADDR, false, &Wire)) {
    Serial.println("# [TOF] Khong tim thay VL53L0X (dia chi 0x29): kiem tra day SDA/SCL, nguon 3.3V");
    return false;
  }
  lox.startRangeContinuous(50);  // do lien tuc moi 50 ms
  tofStarted = true;
  Serial.println("# [TOF] OK");
  return true;
}

void tofPoll() {
  if (!tofStarted) return;
  if (lox.isRangeComplete()) {
    uint16_t mm = lox.readRange();
    // VL53L0X tra ve gia tri rat lon (~8190) khi ngoai tam do hoac loi
    lastMm = (mm == 0 || mm > TOF_FAR_MM) ? TOF_FAR_MM : mm;
  }
}

uint16_t tofMm() { return lastMm; }
bool tofOk() { return tofStarted; }

void i2cScan() {
  if (!wireStarted()) return;
  Serial.println("# [I2C] Dang quet...");
  int found = 0;
  for (uint8_t addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      Serial.printf("# [I2C] Thay thiet bi tai 0x%02X%s\n", addr, addr == 0x29 ? "  <- VL53L0X" : "");
      found++;
    }
  }
  if (found == 0) Serial.println("# [I2C] Khong thay thiet bi nao");
}
