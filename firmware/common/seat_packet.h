#pragma once
#include <stdint.h>

enum MsgType   : uint8_t { MSG_HELLO = 1, MSG_TELEMETRY = 2, MSG_CMD = 3, MSG_ACK = 4 };
enum SeatState : uint8_t { ST_EMPTY = 0, ST_OCCUPIED = 1, ST_OBJECT_ONLY = 2 };
enum AiLabel   : uint8_t { AI_EMPTY = 0, AI_PERSON_STILL = 1, AI_PERSON_MOVE = 2, AI_BAG = 3 };
enum CmdCode   : uint8_t { CMD_WARN = 1, CMD_OTA = 2 };

// Node -> bridge: HELLO (luc khoi dong) va TELEMETRY
typedef struct __attribute__((packed)) {
  uint8_t  type;       // MSG_HELLO hoac MSG_TELEMETRY
  uint8_t  seat_id;    // 1..3
  uint16_t seq;        // tang dan moi goi, de dem mat goi
  uint8_t  state;      // SeatState
  uint8_t  ai_label;   // AiLabel
  uint8_t  ai_conf;    // 0..100
  uint16_t tof_mm;     // khoang cach ToF
  uint16_t obj_secs;   // so giay lien tuc o OBJECT_ONLY, 0 neu khac
  uint8_t  fw_major;
  uint8_t  fw_minor;
} SeatPacket;

// Bridge -> node: CMD; node -> bridge: ACK
typedef struct __attribute__((packed)) {
  uint8_t  type;       // MSG_CMD hoac MSG_ACK
  uint8_t  seat_id;
  uint8_t  cmd;        // CmdCode
  uint8_t  arg;        // CMD_WARN: 1 bat, 0 tat
  uint16_t rid;        // request id, de khop ACK voi lenh
  uint8_t  ok;         // chi dung trong ACK: 1 thanh cong
} CmdPacket;

