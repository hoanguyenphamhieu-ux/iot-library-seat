#include "link.h"

#include <WiFi.h>
#include <esp_arduino_version.h>
#include <esp_now.h>
#include <esp_wifi.h>

#include "config.h"
#include "secrets.h"

static QueueHandle_t cmdQueue = nullptr;

// Chu ky callback nhan khac nhau giua Arduino core 2.x va 3.x.
// Trong callback chi copy du lieu vao hang doi, KHONG Serial.print.
#if ESP_ARDUINO_VERSION_MAJOR >= 3
static void onRecv(const esp_now_recv_info_t *info, const uint8_t *data, int len) {
  (void)info;
#else
static void onRecv(const uint8_t *mac, const uint8_t *data, int len) {
  (void)mac;
#endif
  if (len != (int)sizeof(CmdPacket) || cmdQueue == nullptr) return;
  CmdPacket pkt;
  memcpy(&pkt, data, sizeof(pkt));
  if (pkt.type != MSG_CMD || pkt.seat_id != SEAT_ID) return;
  xQueueSend(cmdQueue, &pkt, 0);
}

String macString() { return WiFi.macAddress(); }

bool linkBegin() {
  cmdQueue = xQueueCreate(8, sizeof(CmdPacket));

  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  esp_wifi_set_channel(ESPNOW_CHANNEL, WIFI_SECOND_CHAN_NONE);

  if (esp_now_init() != ESP_OK) {
    Serial.println("# [ESPNOW] esp_now_init that bai");
    return false;
  }
#if USE_ESPNOW_ENCRYPTION
  esp_now_set_pmk(ESPNOW_PMK);
#endif

  esp_now_peer_info_t peer = {};
  memcpy(peer.peer_addr, BRIDGE_MAC, 6);
  peer.channel = ESPNOW_CHANNEL;
  peer.ifidx = WIFI_IF_STA;
#if USE_ESPNOW_ENCRYPTION
  peer.encrypt = true;
  memcpy(peer.lmk, ESPNOW_LMK, 16);
#else
  peer.encrypt = false;
#endif
  if (esp_now_add_peer(&peer) != ESP_OK) {
    Serial.println("# [ESPNOW] Them peer bridge that bai: kiem tra BRIDGE_MAC trong secrets.h");
    return false;
  }
  esp_now_register_recv_cb(onRecv);

  Serial.printf("# [ESPNOW] OK, kenh %d, ma hoa %s, MAC node %s\n", ESPNOW_CHANNEL,
                USE_ESPNOW_ENCRYPTION ? "BAT" : "TAT", WiFi.macAddress().c_str());
  return true;
}

bool linkSend(const void *data, size_t len) {
  esp_err_t err = esp_now_send(BRIDGE_MAC, (const uint8_t *)data, len);
  if (err != ESP_OK) {
    Serial.printf("# [ESPNOW] Gui loi: %s\n", esp_err_to_name(err));
    return false;
  }
  return true;
}

bool linkPopCmd(CmdPacket &out) {
  if (cmdQueue == nullptr) return false;
  return xQueueReceive(cmdQueue, &out, 0) == pdTRUE;
}
