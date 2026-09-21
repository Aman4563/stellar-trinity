"""Bounded JSONL reporting; explicit output is exclusive-create and never an authority file."""

import argparse
import json
import sys
from collections.abc import Callable, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Final

from tools.attest.canonical import CanonicalizationError
from tools.backfill_disk import children
from tools.backfill_models import (
    BACKFILL_FORBIDDEN_PREFIXES,
    BackfillError,
    BundleDiagnosis,
    Disposition,
    Failure,
)
from tools.forensics.reading import TraceReadError

MAX_BUNDLES: Final = 1024
MAX_OUTPUT_BYTES: Final = 16 * 1024 * 1024


def write_report(reports: Sequence[BundleDiagnosis], destination: Path | None = None) -> None:
    """Write only typed diagnoses, refusing protected paths before opening anything.

    Lexical and resolved checks cover nested roots and symlink aliases. All .audit
    writes are additionally refused because this tool owns no auditor surface.
    Existing files are never overwritten, including hard links to protected bytes.
    """
    if destination is not None:
        for path in (destination.absolute(), destination.resolve()):
            parts = path.parts
            if ".audit" in parts or any(
                parts[index : index + len(Path(prefix).parts)] == Path(prefix).parts
                for prefix in BACKFILL_FORBIDDEN_PREFIXES
                for index in range(len(parts))
            ):
                raise BackfillError(Failure.FORBIDDEN_WRITE)
        if destination.is_symlink() or any(parent.is_symlink() for parent in destination.parents):
            raise BackfillError(Failure.UNSAFE_PATH)
    rows = [json.dumps(asdict(report), sort_keys=True) for report in reports]
    rows.append(
        json.dumps(
            {
                "kind": "summary",
                "bundle_count": len(reports),
                "dispositions": {
                    item.value: sum(report.disposition is item for report in reports)
                    for item in Disposition
                },
                "authority": "diagnosis only",
            },
            sort_keys=True,
        )
    )
    output = "\n".join(rows) + "\n"
    if len(output.encode("utf-8")) > MAX_OUTPUT_BYTES:
        raise BackfillError(Failure.INPUT_TOO_LARGE)
    if destination is None:
        print(output, end="")
    else:
        with destination.open("x", encoding="utf-8") as stream:
            stream.write(output)


def run_cli(
    argv: Sequence[str],
    diagnose: Callable[[Path], BundleDiagnosis],
    *,
    project_root: Path | None = None,
) -> int:
    parser = argparse.ArgumentParser(description="Diagnose history without certifying it (JSONL).")
    parser.add_argument("corpus", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    root: Path = args.corpus
    destination: Path | None = args.output
    try:
        entries = children(root, project_root=project_root)
        bundles = (root,) if (root / "trajectories").is_dir() else entries
        if not bundles or len(bundles) > MAX_BUNDLES:
            raise BackfillError(Failure.INPUT_TOO_LARGE)
        reports = tuple(diagnose(bundle) for bundle in bundles)
        write_report(reports, destination)
    except BackfillError as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 2
    except (OSError, TraceReadError, CanonicalizationError, RecursionError):
        print(json.dumps({"error": Failure.MALFORMED.value}), file=sys.stderr)
        return 2
    return 0
