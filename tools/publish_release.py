# -*- coding: utf-8 -*-
"""Publish a signed APK to this distribution repo's GitHub Releases.

Usage (from the build directory, after build_apk_final.py + sign_v2.py):

    python tools/publish_release.py \
        --apk  _build/qnzl-local-v152-signed.apk \
        --version-code 152 --version-name v152 \
        --changelog-file 灰度测试发布说明-v152.md

What it does:
  1. Computes the APK's size and SHA-256.
  2. Regenerates update.json (the fixed-address update manifest the in-game
     updater reads) next to this script's repo root.
  3. Creates (or replaces assets of) the GitHub release tagged v<versionCode>
     and uploads both the APK and update.json.
  4. Commits the new update.json to the repo so the manifest history is
     versioned too.

Refuses to publish a versionCode that is not greater than the one already in
update.json — downgrades would silently break every installed client.

Requires the GitHub CLI (`gh`) logged in with the `repo` scope.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
UPDATE_JSON = REPO_ROOT / "update.json"

GH_CANDIDATES = [
    shutil.which("gh"),
    r"C:\Program Files\GitHub CLI\gh.exe",
]


def gh_exe() -> str:
    for candidate in GH_CANDIDATES:
        if candidate and Path(candidate).exists():
            return str(candidate)
    raise SystemExit("gh CLI not found; install GitHub CLI first")


def run(args: list[str]) -> None:
    result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise SystemExit(f"command failed: {' '.join(args)}\n{result.stderr or result.stdout}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apk", required=True, help="signed APK to publish")
    parser.add_argument("--version-code", required=True, type=int)
    parser.add_argument("--version-name", required=True)
    parser.add_argument("--changelog", default="")
    parser.add_argument("--changelog-file", default="")
    parser.add_argument("--notes", default="", help="release notes; defaults to changelog")
    parser.add_argument("--min-version-code", type=int, default=0)
    args = parser.parse_args()

    apk = Path(args.apk)
    if not apk.is_file():
        raise SystemExit(f"APK not found: {apk}")
    if not args.version_name.startswith("v"):
        raise SystemExit("version-name must look like vNNN")
    if int(args.version_name[1:]) != args.version_code:
        raise SystemExit("version-name and version-code disagree")

    changelog = args.changelog
    if args.changelog_file:
        changelog = Path(args.changelog_file).read_text(encoding="utf-8").strip()
    notes = args.notes or changelog or args.version_name

    previous = json.loads(UPDATE_JSON.read_text(encoding="utf-8")) if UPDATE_JSON.exists() else None
    if previous and int(previous["versionCode"]) >= args.version_code:
        raise SystemExit(
            f"update.json already carries versionCode {previous['versionCode']}; "
            f"refusing to publish {args.version_code}"
        )

    digest = hashlib.sha256()
    size = 0
    with open(apk, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
            size += len(chunk)

    manifest = {
        "versionCode": args.version_code,
        "versionName": args.version_name,
        "apkFile": apk.name,
        "size": size,
        "sha256": digest.hexdigest(),
        "minVersionCode": args.min_version_code,
        "publishedAt": datetime.date.today().isoformat(),
        "changelog": changelog,
    }
    UPDATE_JSON.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"update.json: {args.version_name} size={size} sha256={digest.hexdigest()[:12]}…")

    gh = gh_exe()
    tag = args.version_name
    # Release existence check; create or reuse.
    probe = subprocess.run(
        [gh, "release", "view", tag], capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    if probe.returncode != 0:
        run([gh, "release", "create", tag, "--title", f"本地版 {args.version_name}",
             "--notes", notes])
    run([gh, "release", "upload", tag, str(apk), str(UPDATE_JSON), "--clobber"])
    print(f"published {tag}: {apk.name} + update.json")

    run(["git", "-C", str(REPO_ROOT), "add", "update.json"])
    run(["git", "-C", str(REPO_ROOT), "commit", "-m",
         f"release {args.version_name} (versionCode {args.version_code})"])
    run(["git", "-C", str(REPO_ROOT), "push"])
    print("repo manifest committed and pushed")


if __name__ == "__main__":
    main()
