#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 yulei
"""Build the source-only Blender Extensions ZIP with files at its root."""

from pathlib import Path
import hashlib
import json
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'extension'
DIST = ROOT / 'dist'
DIST.mkdir(exist_ok=True)
# Keep the extension's Free-only instructions separate from the repository's
# comparison and optional Full-version link.
shutil.copyfile(ROOT / 'THIRD_PARTY_NOTICES.md', SOURCE / 'THIRD_PARTY_NOTICES.md')
path = DIST / 'seamwick_uv_free-0.1.0.zip'
files = sorted(
    item for item in SOURCE.iterdir()
    if item.is_file() and (item.suffix in {'.py', '.toml', '.md'} or item.name == 'LICENSE')
)
with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
    for item in files:
        info = zipfile.ZipInfo(item.name, date_time=(2026, 10, 2, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        archive.writestr(info, item.read_bytes())
digest = hashlib.sha256(path.read_bytes()).hexdigest()
(DIST / 'SHA256SUMS.txt').write_text(f'{digest}  {path.name}\n', encoding='utf-8')
print(json.dumps({'zip': str(path), 'sha256': digest, 'files': [item.name for item in files]}, indent=2))
