"""Snowflake-style ID generator with an additional random component."""

from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass


@dataclass
class SnowflakeGenerator:
    """Generate sortable identifiers using a Snowflake-like scheme."""

    epoch_ms: int = 1704067200000  # 2024-01-01T00:00:00Z
    sequence_bits: int = 12
    random_bits: int = 10

    def __post_init__(self) -> None:
        self._lock = threading.Lock()
        self._last_timestamp = -1
        self._sequence = 0
        self._sequence_mask = (1 << self.sequence_bits) - 1
        self._random_mask = (1 << self.random_bits) - 1
        self._timestamp_shift = self.sequence_bits + self.random_bits

    def generate_id(self) -> int:
        """Return a unique, roughly time-ordered integer."""
        with self._lock:
            timestamp = self._current_millis()
            if timestamp < self._last_timestamp:  # pragma: no cover - defensive branch
                timestamp = self._last_timestamp

            if timestamp == self._last_timestamp:
                self._sequence = (self._sequence + 1) & self._sequence_mask
                if self._sequence == 0:
                    timestamp = self._wait_next_millis(self._last_timestamp)
            else:
                self._sequence = 0

            self._last_timestamp = timestamp
            random_bits = random.getrandbits(self.random_bits) & self._random_mask

        return (
            ((timestamp - self.epoch_ms) << self._timestamp_shift)
            | (self._sequence << self.random_bits)
            | random_bits
        )

    def _current_millis(self) -> int:
        return int(time.time() * 1000)

    def _wait_next_millis(self, last_timestamp: int) -> int:
        timestamp = self._current_millis()
        while timestamp <= last_timestamp:
            time.sleep(0.0001)
            timestamp = self._current_millis()
        return timestamp
