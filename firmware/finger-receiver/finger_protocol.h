#pragma once
#include <stdint.h>
#include <string.h>

namespace fingers {
inline bool parseUnsigned(const char* text, uint32_t maximum, uint32_t& value) {
  if (!text || !*text) return false;
  uint32_t result = 0;
  for (const char* p = text; *p; ++p) {
    if (*p < '0' || *p > '9') return false;
    const uint32_t digit = *p - '0';
    if (digit > maximum || result > (maximum - digit) / 10) return false;
    result = result * 10 + digit;
  }
  value = result;
  return true;
}

inline uint8_t handCode(const char* name) {
  if (!strcmp(name, "nenhuma")) return 0;
  if (!strcmp(name, "direita")) return 1;
  if (!strcmp(name, "esquerda")) return 2;
  return 255;
}

inline const char* handName(uint8_t code) {
  return code == 1 ? "direita" : code == 2 ? "esquerda" : "nenhuma";
}

inline bool validState(uint32_t mask, uint32_t tracking, uint8_t hand) {
  if (mask > 15 || tracking > 1 || hand > 2) return false;
  return tracking ? hand != 0 : mask == 0 && hand == 0;
}
}  // namespace fingers
