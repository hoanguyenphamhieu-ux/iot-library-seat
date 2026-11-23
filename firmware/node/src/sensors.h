// sensors.h - Doc radar LD2410C (UART) va ToF VL53L0X (I2C).
#pragma once
#include <Arduino.h>

struct RadarFrame {
  bool valid = false;          // da nhan it nhat 1 khung du lieu
  bool presence = false;       // radar bao co nguoi (dong hoac tinh)
  bool moving = false;         // co muc tieu chuyen dong
  bool stationary = false;     // co muc tieu dung yen
  uint8_t moveE[9] = {0};      // nang luong chuyen dong tung gate (engineering mode)
  uint8_t stillE[9] = {0};     // nang luong tinh tung gate
  uint32_t lastMs = 0;         // thoi diem nhan khung moi nhat
};

// ----- Radar -----
bool radarBegin();                       // mo UART, bat engineering mode
void radarPoll();                        // goi lien tuc trong loop()
const RadarFrame &radarFrame();
bool radarFresh(uint32_t maxAgeMs = 1000);  // con nhan du lieu gan day?
bool radarApplyMaxGate(uint8_t gate, uint8_t noOneWindowS);

// ----- ToF -----
bool tofBegin();                         // Wire.begin + khoi dong VL53L0X o che do lien tuc
void tofPoll();                          // goi lien tuc trong loop()
uint16_t tofMm();                        // khoang cach (mm), TOF_FAR_MM neu khong do duoc
bool tofOk();

// ----- Tien ich -----
void i2cScan();                          // in cac dia chi I2C tim thay
