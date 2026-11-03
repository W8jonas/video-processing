#pragma once

// Proposta apos montagem em 02/11: D0, D1, D2 e D7.
// Troca de D3 por D7 e DHT desconectado de D2 confirmados em 02/11.
// Copiar para leds_config.h e habilitar apenas para uma montagem confirmada.
// Um resistor por LED. GPIO -> resistor -> anodo; catodo -> GND.
constexpr bool kFingerLedsEnabled = false;
constexpr uint8_t kFingerLedPins[4] = {D0, D1, D2, D7};
