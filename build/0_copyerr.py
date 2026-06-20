"""
SOFiSTiK .err File Copier
Copies .err files from SOFiSTiK installation directories into build version folders.

Source:  C:/Program Files/SOFiSTiK/{year}/SOFiSTiK {year}/*.err
Target:  build/{year}/*.err
"""

import shutil
from pathlib import Path

SOFISTIK_ROOT = Path("C:/Program Files/SOFiSTiK")

VERSIONS = ['2018', '2020', '2022', '2023', '2024', '2025', '2026']

def copy_err_files(version, build_dir):
    src_dir = SOFISTIK_ROOT / version / f"SOFiSTiK {version}"
    dst_dir = build_dir / version

    if dst_dir.exists():
        for f in dst_dir.glob("*.err"):
            f.unlink()

    if not src_dir.exists():
        print(f"  {version}: source not found ({src_dir})")
        return 0

    dst_dir.mkdir(parents=True, exist_ok=True)

    err_files = sorted(src_dir.glob("*.err"))
    if not err_files:
        print(f"  {version}: no .err files found in {src_dir}")
        return 0

    copied = 0
    for f in err_files:
        stem = f.stem.upper()
        if stem.endswith('_TEST') or stem.startswith('TEST_') or stem == 'TABLELAYOUT':
            continue
        shutil.copy2(f, dst_dir / f.name)
        copied += 1

    print(f"  {version}: copied {copied}/{len(err_files)} .err files (skipped {len(err_files) - copied} test files)")
    return copied


def main():
    build_dir = Path(__file__).parent

    print("SOFiSTiK .err File Copier")
    print("=" * 50)

    total = 0
    for version in VERSIONS:
        total += copy_err_files(version, build_dir)

    print("=" * 50)
    print(f"Total: {total} files copied")


if __name__ == '__main__':
    main()
