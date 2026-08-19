#!/usr/bin/env python3
"""Build a clean, secret-free TAFA M7 paper/demo ZIP and SHA-256 checksum."""
from __future__ import annotations

import argparse
import hashlib
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKIP_NAMES = {".env", ".DS_Store", "bot.pid", "live_status.json", "runtime_config.json"}
SKIP_PARTS = {"__pycache__", ".pytest_cache", ".git", "logs"}
SKIP_SUFFIXES = {".pyc", ".pyo", ".db", ".sqlite", ".log"}


def should_include(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    if path.name in SKIP_NAMES or path.suffix.lower() in SKIP_SUFFIXES:
        return False
    return not any(part in SKIP_PARTS for part in relative.parts)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Package TAFA M7 paper/demo release.")
    parser.add_argument("--output", type=Path, default=ROOT.parent / "TAFA_X_ELITE_M7_PAPER_DEMO_OKX.zip")
    args = parser.parse_args()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    top = ROOT.name
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(ROOT.rglob("*")):
            if path.is_file() and should_include(path):
                archive.write(path, Path(top) / path.relative_to(ROOT))

    checksum = sha256(output)
    checksum_path = output.with_suffix(output.suffix + ".sha256")
    checksum_path.write_text(f"{checksum}  {output.name}\n", encoding="utf-8")
    with zipfile.ZipFile(output, "r") as archive:
        invalid = archive.testzip()
    if invalid:
        raise RuntimeError(f"archive integrity failed at {invalid}")
    print(f"M7 package: {output}")
    print(f"SHA-256: {checksum}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
