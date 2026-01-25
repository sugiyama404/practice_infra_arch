"""Utilities for Base62 encoding."""

from typing import Final

_ALPHABET: Final[str] = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
_BASE: Final[int] = len(_ALPHABET)


def encode(number: int) -> str:
    """Encode a non-negative integer into a Base62 string."""
    if number < 0:
        raise ValueError("Base62 encoding only supports non-negative integers")
    if number == 0:
        return _ALPHABET[0]

    encoded: list[str] = []
    value = number
    while value:
        value, remainder = divmod(value, _BASE)
        encoded.append(_ALPHABET[remainder])
    encoded.reverse()
    return "".join(encoded)


def decode(encoded: str) -> int:
    """Decode a Base62 string back into an integer."""
    value = 0
    for char in encoded:
        try:
            index = _ALPHABET.index(char)
        except ValueError as exc:  # pragma: no cover - defensive branch
            raise ValueError(f"Invalid Base62 character: {char}") from exc
        value = value * _BASE + index
    return value
