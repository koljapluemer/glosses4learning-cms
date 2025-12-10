from __future__ import annotations


def parse_key_value_lines(value: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in (value or "").splitlines():
        if not line.strip():
            continue
        if ":" in line:
            key, val = line.split(":", 1)
            result[key.strip()] = val.strip()
        else:
            result[line.strip()] = ""
    return result
