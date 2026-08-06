from __future__ import annotations

from pathlib import Path

import yaml


SMART_QUOTES = {
    "\u201c": 'Use normal double quote " instead of Chinese left double quote.',
    "\u201d": 'Use normal double quote " instead of Chinese right double quote.',
    "\u2018": "Use normal single quote ' instead of Chinese left single quote.",
    "\u2019": "Use normal single quote ' instead of Chinese right single quote.",
}


def main() -> int:
    paths = [Path("data/test_data.yaml"), *sorted(Path("data/test_data").glob("*.yaml"))]
    errors: list[str] = []

    for path in paths:
        text = path.read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), start=1):
            for quote, message in SMART_QUOTES.items():
                column = line.find(quote)
                if column != -1:
                    errors.append(f"{path}:{line_number}:{column + 1}: {message}\n  {line}")

        try:
            yaml.safe_load(text)
        except yaml.YAMLError as exc:
            errors.append(f"{path}: YAML syntax error:\n{exc}")

    if errors:
        print("test data validation failed:\n")
        print("\n\n".join(errors))
        return 1

    print(f"test data validation passed. Checked {len(paths)} file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
