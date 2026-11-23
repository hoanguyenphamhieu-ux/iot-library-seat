// config.h - Thong so cua node ghe. Cac so nay chinh sau khi do thuc te (buoc A3).
#pragma once

#define FW_VERSION_MAJOR 1
#define FW_VERSION_MINOR 0

#ifndef SEAT_ID
#define SEAT_ID 1            // ghi de bang build flag -D SEAT_ID=2 trong platformio.ini
#endif

// ---------- ESP-NOW ----------
#define ESPNOW_CHANNEL 1

// ---------- Nhip thoi gian (CONTRACT 3.2, DATAFLOW muc 9) ----------
#define SAMPLE_PERIOD_MS     100    // doc cam bien 10 Hz
#define DECIDE_PERIOD_MS     500    // quyet dinh trang thai 2 lan/giay
#define DEBOUNCE_MS         3000    // trang thai moi phai giu 3 giay
#define HEARTBEAT_MS       10000    // heartbeat 10 giay

// ---------- Nguong ----------
// Khoang cach ToF nho hon nguong nay = co vat/nguoi tren ghe.
// Cach chon (buoc A3): do khi ghe trong, lay ket qua tru di khoang 100 mm.
#define TOF_OBJECT_MM        400
#define TOF_FAR_MM          2000    // ToF tra ve gia tri lon/khong hop le thi coi nhu "xa"

// Gioi han tam do radar: gate 2 ~ 1.5 m (moi gate ~0.75 m). Nap 1 lan, radar tu luu.
#define RADAR_MAX_GATE         2
#define RADAR_NO_ONE_WINDOW_S  2    // so giay khong thay nguoi thi radar bao "khong co"
