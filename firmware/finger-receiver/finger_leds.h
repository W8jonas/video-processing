#pragma once
#include <stdint.h>

namespace fingers {
// Enabled explicitly only after the proposed pins and wiring are confirmed.
// Writer receives a GPIO and a logical active-high level.
template <typename Writer>
void applyLeds(uint8_t mask, bool tracking, bool enabled,
               const uint8_t (&pins)[4], Writer write) {
  if (!enabled) return;
  for (uint8_t i = 0; i < 4; ++i) {
    write(pins[i], tracking && (mask & (1 << i)) ? 1 : 0);
  }
}
}  // namespace fingers
