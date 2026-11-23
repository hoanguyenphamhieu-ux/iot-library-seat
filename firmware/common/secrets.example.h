// secrets.example.h - MAU. Copy thanh secrets.h (cung thu muc) roi dien gia tri that.
// secrets.h da nam trong .gitignore, KHONG BAO GIO commit secrets.h.
#pragma once
#include <stdint.h>

// ---------- MAC (lay bang che do "hello", xem firmware/README.md buoc 2) ----------
// MAC cua node bridge: node ghe gui ESP-NOW toi dia chi nay.
static const uint8_t BRIDGE_MAC[6] = {0x00, 0x00, 0x00, 0x00, 0x00, 0x00};

// MAC cua cac node ghe, theo thu tu seat_id: phan tu 0 = Seat-01, 1 = Seat-02, ...
// Bridge chi can danh sach nay khi bat ma hoa ESP-NOW.
static const uint8_t NODE_MACS[][6] = {
    {0x00, 0x00, 0x00, 0x00, 0x00, 0x00},  // Seat-01
    {0x00, 0x00, 0x00, 0x00, 0x00, 0x00},  // Seat-02
};

// ---------- Ma hoa ESP-NOW (cai tien da chot) ----------
// De 0 khi moi bat dau. Chay on dinh khong ma hoa roi moi doi thanh 1 o CA node va bridge.
#define USE_ESPNOW_ENCRYPTION 0
// 16 byte bat ky, PHAI giong nhau tren tat ca cac mach. Doi sang chuoi ngau nhien cua nhom.
static const uint8_t ESPNOW_PMK[16] = {'p','m','k','-','d','o','i','-','c','h','u','o','i','-','n','a'};
static const uint8_t ESPNOW_LMK[16] = {'l','m','k','-','d','o','i','-','c','h','u','o','i','-','n','a'};

// ---------- Dung cho OTA (buoc A6, chua dung bay gio) ----------
#define WIFI_SSID   "ten_wifi"
#define WIFI_PASS   "mat_khau_wifi"
#define SEAT1_TOKEN "access_token_cua_Seat-01"
#define SEAT2_TOKEN "access_token_cua_Seat-02"
