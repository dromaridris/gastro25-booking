"""CLI for Clinical Intelligence knowledge tools.

Usage:
  python -m clinical_intelligence.cli validate
  python -m clinical_intelligence.cli import FILE --dest REL [--dry-run]
  python -m clinical_intelligence.cli reload
  python -m clinical_intelligence.cli version
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="clinical_intelligence.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("validate", help="Validate core clinical_knowledge packs")
    sub.add_parser("version", help="Show knowledge version / evidence registry")
    sub.add_parser("reload", help="Clear in-process knowledge caches")

    p_imp = sub.add_parser("import", help="Validate and optionally install a JSON pack")
    p_imp.add_argument("file", type=Path)
    p_imp.add_argument("--dest", required=True, help="Relative path under clinical_knowledge/")
    p_imp.add_argument("--dry-run", action="store_true")

    args = parser.parse_args(argv)

    if args.cmd == "validate":
        from clinical_intelligence import knowledge_importer
        result = knowledge_importer.validate_tree()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result.get("ok") else 1

    if args.cmd == "version":
        from clinical_intelligence import evidence_service
        print(json.dumps(evidence_service.knowledge_version_info(), indent=2, ensure_ascii=False))
        return 0

    if args.cmd == "reload":
        from clinical_intelligence import evidence_service
        print(json.dumps(evidence_service.reload_knowledge(reason="cli"), indent=2))
        return 0

    if args.cmd == "import":
        from clinical_intelligence import knowledge_importer
        result = knowledge_importer.install_pack(args.file, dest_relative=args.dest, dry_run=args.dry_run)
        # Drop raw data if present
        result.pop("data", None)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result.get("ok") else 1

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
