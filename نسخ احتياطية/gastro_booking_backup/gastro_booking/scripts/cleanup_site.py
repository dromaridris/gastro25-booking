#!/usr/bin/env python3
"""Clean disposable site artifacts (caches, orphan uploads). Safe by default.

Does NOT delete:
  - patient_documents
  - ercp_images / procedure images
  - source code, templates, clinical_knowledge
  - gastro_booking.db (pass --vacuum-db only with care)

Usage:
  python scripts/cleanup_site.py           # dry-run
  python scripts/cleanup_site.py --apply   # actually delete
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Relative dirs whose *contents* may be wiped if they are orphan uploads
ORPHAN_UPLOAD_DIRS = (
    "data/import_uploads",
    "data/mcq_bank_uploads",
)

# Never touch these trees
PROTECTED_PREFIXES = (
    "data/patient_documents",
    "ercp_images",
    "colonoscopy_v2_images",
    "dilatation_images",
    "clinical_knowledge",
    "templates",
    "static",
)


def _is_protected(path: Path) -> bool:
    try:
        rel = path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return True
    return any(rel == p or rel.startswith(p + "/") for p in PROTECTED_PREFIXES)


def collect_targets() -> list[tuple[Path, str]]:
    targets: list[tuple[Path, str]] = []

    for dirpath, dirnames, filenames in os.walk(ROOT):
        p = Path(dirpath)
        # skip .git
        if ".git" in p.parts:
            dirnames[:] = []
            continue
        if _is_protected(p):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            continue
        if p.name == "__pycache__":
            targets.append((p, "pycache dir"))
            dirnames[:] = []
            continue
        for name in filenames:
            fp = p / name
            if name.endswith((".pyc", ".pyo")):
                targets.append((fp, "bytecode"))
            elif name.endswith((".log", ".tmp", ".bak", ".orig")):
                targets.append((fp, "temp/log"))

    for rel in ORPHAN_UPLOAD_DIRS:
        d = ROOT / rel
        if not d.is_dir():
            continue
        for fp in d.iterdir():
            if fp.is_file():
                targets.append((fp, "orphan upload"))

    # Deduplicate (parent pycache covers children)
    uniq: dict[str, tuple[Path, str]] = {}
    for path, kind in targets:
        key = str(path.resolve())
        uniq[key] = (path, kind)
    return sorted(uniq.values(), key=lambda x: str(x[0]))


def human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def path_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            try:
                total += (Path(root) / f).stat().st_size
            except OSError:
                pass
    return total


def main() -> int:
    ap = argparse.ArgumentParser(description="Clean disposable Gastro site files")
    ap.add_argument("--apply", action="store_true", help="Actually delete (default is dry-run)")
    args = ap.parse_args()

    targets = collect_targets()
    total = sum(path_size(p) for p, _ in targets)
    print(f"Root: {ROOT}")
    print(f"Found {len(targets)} target(s), ~{human_size(total)}")
    by_kind: dict[str, int] = {}
    for _, kind in targets:
        by_kind[kind] = by_kind.get(kind, 0) + 1
    for k, v in sorted(by_kind.items()):
        print(f"  {k}: {v}")

    if not args.apply:
        print("\nDry-run only. Re-run with --apply to delete.")
        for path, kind in targets[:40]:
            print(f"  [{kind}] {path.relative_to(ROOT)}")
        if len(targets) > 40:
            print(f"  ... +{len(targets) - 40} more")
        return 0

    removed = 0
    freed = 0
    for path, kind in targets:
        try:
            sz = path_size(path)
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=False)
            else:
                path.unlink(missing_ok=True)
            removed += 1
            freed += sz
            print(f"removed [{kind}] {path.relative_to(ROOT)}")
        except OSError as exc:
            print(f"SKIP {path}: {exc}", file=sys.stderr)

    print(f"\nDone. Removed {removed} item(s), freed ~{human_size(freed)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
