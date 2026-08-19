"""Static audit utility for externally supplied TAFA artifacts.

This program deliberately performs no import, execution, extraction, or
deserialization of supplied artifacts. It only reads bytes, parses Python
syntax using ``ast`` and reviews ZIP central-directory metadata / source text.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile


RISKY_CALLS = {
    "eval",
    "exec",
    "compile",
    "system",
    "Popen",
    "run",
    "call",
    "load",
    "loads",
    "place_order",
    "private_post",
    "private_get",
}
RISKY_IMPORT_ROOTS = {"pickle", "joblib", "subprocess", "requests", "websockets"}
RUNTIME_MARKERS = (".env", ".db", ".sqlite", ".log", "venv/", "__pycache__/")
MODEL_MARKERS = (b"sklearn", b"HistGradientBoosting", b"numpy", b"joblib", b"subprocess", b"os.system")
MAX_SOURCE_BYTES = 2_000_000


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = dotted_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def audit_python_bytes(raw: bytes, label: str) -> dict[str, object]:
    result: dict[str, object] = {
        "label": label,
        "bytes": len(raw),
        "syntax": "not_parsed",
        "imports": [],
        "risky_calls": [],
    }
    try:
        source = raw.decode("utf-8")
    except UnicodeDecodeError:
        result["syntax"] = "non_utf8_source"
        return result
    try:
        tree = ast.parse(source, filename=label)
    except SyntaxError as exc:
        result["syntax"] = "syntax_error"
        result["syntax_error"] = {"line": exc.lineno, "message": exc.msg}
        return result
    result["syntax"] = "parsed"
    imports: set[str] = set()
    calls: list[dict[str, object]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add(node.module or "")
        elif isinstance(node, ast.Call):
            name = dotted_name(node.func)
            leaf = name.rsplit(".", 1)[-1]
            if leaf in RISKY_CALLS:
                calls.append({"line": getattr(node, "lineno", None), "call": name})
    result["imports"] = sorted(imports)
    result["risky_imports"] = sorted(
        root for root in {item.split(".", 1)[0] for item in imports} if root in RISKY_IMPORT_ROOTS
    )
    result["risky_calls"] = calls[:250]
    return result


def audit_model(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    return {
        "path": str(path),
        "bytes": len(raw),
        "sha256": sha256(path),
        "pickle_protocol_marker": raw[:2].hex(),
        "appears_pickle_protocol": len(raw) >= 2 and raw[0] == 0x80 and raw[1] in {4, 5},
        "byte_markers": [marker.decode("ascii") for marker in MODEL_MARKERS if marker in raw],
        "deserialized": False,
    }


def safe_archive_member(name: str) -> bool:
    pure = PurePosixPath(name)
    return not pure.is_absolute() and ".." not in pure.parts


def audit_zip(path: Path) -> dict[str, object]:
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        source_audits: list[dict[str, object]] = []
        skipped_sources: list[str] = []
        runtime_entries = []
        unsafe_paths = []
        for info in infos:
            name = info.filename
            lower = name.lower()
            if not safe_archive_member(name):
                unsafe_paths.append(name)
            if any(marker in lower for marker in RUNTIME_MARKERS):
                runtime_entries.append(name)
            if lower.endswith(".py") and "/venv/" not in lower and "/__pycache__/" not in lower:
                if info.file_size > MAX_SOURCE_BYTES:
                    skipped_sources.append(name)
                    continue
                source_audits.append(audit_python_bytes(archive.read(info), f"{path.name}:{name}"))
        return {
            "path": str(path),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "entries": len(infos),
            "encrypted_entries": sum(1 for info in infos if info.flag_bits & 0x1),
            "unsafe_member_paths": unsafe_paths,
            "runtime_artifact_count": len(runtime_entries),
            "runtime_artifact_examples": runtime_entries[:100],
            "python_sources_audited": len(source_audits),
            "python_sources_skipped_size": skipped_sources,
            "python_audits": source_audits,
            "extracted": False,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Passive static audit only")
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    report: dict[str, object] = {"audit_mode": "static_only_no_execution", "artifacts": []}
    for path in args.paths:
        if not path.is_file():
            report["artifacts"].append({"path": str(path), "error": "not_a_file"})
            continue
        suffix = path.suffix.lower()
        if suffix == ".py":
            payload = audit_python_bytes(path.read_bytes(), str(path))
            payload.update({"path": str(path), "sha256": sha256(path)})
        elif suffix == ".zip":
            payload = audit_zip(path)
        elif suffix in {".pkl", ".pickle", ".joblib"}:
            payload = audit_model(path)
        else:
            payload = {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path), "kind": "unclassified"}
        report["artifacts"].append(payload)
    print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
