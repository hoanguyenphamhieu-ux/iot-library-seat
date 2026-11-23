// status_led.h - Dieu khien NeoPixel tren YoloUNO.
#pragma once
#include <Arduino.h>

enum class LedColor : uint8_t { Off, Green, Red, Orange, Yellow, Blue, Purple, White };

void ledBegin();
void ledShow(LedColor color);                    // hien mot mau co dinh ngay lap tuc
void ledUpdate(LedColor base, bool warning);     // goi trong loop(): warning -> nhay vang 2 Hz
bool ledAvailable();
