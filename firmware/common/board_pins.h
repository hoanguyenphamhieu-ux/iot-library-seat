// board_pins.h - So chan GPIO tren YoloUNO (theo so do chan cua OhStem), dung chung cho node va bridge.
//
// Dau noi node ghe (chu in tren mach -> chan linh kien):
//   LD2410C: 5V -> VCC, GND -> GND, D9 (GPIO18) -> TX cua radar, D8 (GPIO17) -> RX cua radar
//   VL53L0X: 3.3V -> VIN, GND -> GND, SDA (GPIO11) -> SDA, SCL (GPIO12) -> SCL
//            (hoac cam vao cong STEMMA QT / Grove I2C neu module co dau noi)
//
// Luu y: A4 va A5 dung chung GPIO11/12 voi SDA/SCL -> khong dung A4, A5 cho viec khac.
// Tranh: D0/D1 (GPIO44/43, UART0), A2 (GPIO3, chan strapping), GPIO0 (nut BOOT).
#pragma once

#define LED_PIN        45   // NeoPixel co san tren mach
#define LED_COUNT       1

// Radar LD2410C (UART1). RX cua mach noi TX cua radar, va nguoc lai.
#define RADAR_RX_PIN   18   // D9  -> noi voi chan TX cua LD2410C
#define RADAR_TX_PIN   17   // D8  -> noi voi chan RX cua LD2410C

// ToF VL53L0X (I2C)
#define I2C_SDA_PIN    11   // SDA (cung chan voi A4)
#define I2C_SCL_PIN    12   // SCL (cung chan voi A5)