#include "status_led.h"

#include <Adafruit_NeoPixel.h>

#include "board_pins.h"

static Adafruit_NeoPixel *strip = nullptr;

static uint32_t toRgb(LedColor c) {
  switch (c) {
    case LedColor::Green:  return Adafruit_NeoPixel::Color(0, 150, 0);
    case LedColor::Red:    return Adafruit_NeoPixel::Color(150, 0, 0);
    case LedColor::Orange: return Adafruit_NeoPixel::Color(160, 60, 0);
    case LedColor::Yellow: return Adafruit_NeoPixel::Color(150, 120, 0);
    case LedColor::Blue:   return Adafruit_NeoPixel::Color(0, 0, 150);
    case LedColor::Purple: return Adafruit_NeoPixel::Color(110, 0, 140);
    case LedColor::White:  return Adafruit_NeoPixel::Color(90, 90, 90);
    case LedColor::Off:
    default:               return 0;
  }
}

void ledBegin() {
  if (LED_PIN < 0) {
    Serial.println("# [LED] LED_PIN = -1, chua dien so chan trong board_pins.h -> bo qua LED");
    return;
  }
  strip = new Adafruit_NeoPixel(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);
  strip->begin();
  strip->setBrightness(60);
  strip->clear();
  strip->show();
}

bool ledAvailable() { return strip != nullptr; }

void ledShow(LedColor color) {
  if (!strip) return;
  uint32_t rgb = toRgb(color);
  for (int i = 0; i < LED_COUNT; i++) strip->setPixelColor(i, rgb);
  strip->show();
}

void ledUpdate(LedColor base, bool warning) {
  static LedColor shown = LedColor::Off;
  static bool first = true;
  LedColor want = base;
  if (warning) {
    // nhay vang 2 Hz: 250 ms sang, 250 ms tat
    want = ((millis() / 250) % 2 == 0) ? LedColor::Yellow : LedColor::Off;
  }
  if (first || want != shown) {  // chi ghi ra LED khi doi mau, tranh nhay nhieu
    ledShow(want);
    shown = want;
    first = false;
  }
}
