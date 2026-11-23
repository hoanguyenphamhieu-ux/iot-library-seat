// link.h - ESP-NOW giua node ghe va bridge.
#pragma once
#include <Arduino.h>

#include "seat_packet.h"

bool linkBegin();                                 // WiFi STA, kenh co dinh, esp_now, peer bridge
bool linkSend(const void *data, size_t len);      // gui toi bridge
bool linkPopCmd(CmdPacket &out);                  // lay lenh nhan duoc (neu co)
String macString();                               // MAC cua chinh mach nay
