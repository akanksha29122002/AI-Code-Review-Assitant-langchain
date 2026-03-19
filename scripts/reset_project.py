from __future__ import annotations

import argparse
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

GENERATED_FILES = [
    DATA_DIR / "review_history.db",
    DATA_DIR / "test_review_history.db",
    DATA_DIR / "test_delivery_history.db",
    DATA_DIR / "test_dedupe_history.db",
    DATA_DIR / "repository_index.json",
]

GENERATED_DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
}

TEMP_DIR_PREFIXES = ("tmp",)


def remove_path(path: Path) -> bool:
    if not path.exists():
        return False
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    else:
        path.unlink(missing_ok=True)
    return True


def iter_generated_dirs() -> list[Path]:
    results: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_dir():
            continue
        if path.name in GENERATED_DIR_NAMES:
            results.append(path)
            continue
        if path.parent == ROOT and path.name.startswith(TEMP_DIR_PREFIXES):
            results.append(path)
    return results


def reset_project(reset_env: bool) -> tuple[list[Path], list[Path]]:
    removed: list[Path] = []
    skipped: list[Path] = []

    for path in GENERATED_FILES:
        if remove_path(path):
            removed.append(path)

    for path in iter_generated_dirs():
        if remove_path(path):
            removed.append(path)
        elif path.exists():
            skipped.append(path)

    if reset_env:
        env_example = ROOT / ".env.example"
        env_file = ROOT / ".env"
        if env_example.exists():
            env_file.write_text(env_example.read_text(encoding="utf-8"), encoding="utf-8")
            removed.append(env_file)

    return removed, skipped


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reset generated project state for the AI code review assistant."
    )
    parser.add_argument(
        "--reset-env",
        action="store_true",
        help="Replace .env with the template from .env.example.",
    )
    args = parser.parse_args()

    removed, skipped = reset_project(reset_env=args.reset_env)

    print("Project reset complete")
    if removed:
        print("")
        print("Removed or recreated:")
        for path in sorted(removed):
            print(f"- {path.relative_to(ROOT)}")

    if skipped:
        print("")
        print("Skipped:")
        for path in sorted(skipped):
            print(f"- {path.relative_to(ROOT)}")

    if not args.reset_env:
        print("")
        print(".env was preserved. Re-run with --reset-env to restore template values.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
