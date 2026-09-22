# -*- coding: utf-8 -*-
"""Build and publish the hot-update channel (files.json + blob pool).

Two modes:

* Full-release follow-up (called by publish_release.py after an APK release):
  records the released build as the new baseline and republishes files.json
  against it.  Devices on the fresh APK then diff to zero downloads.

* Hot fix (`--hot-only`): ships resource/content changes without an APK
  release.  The manifest keeps the RELEASED baseline's identity so installed
  clients accept it, while its file entries describe the NEW desired bytes
  taken from a locally rebuilt (unsigned is fine) APK:

      cd _build && python build_apk_final.py /tmp/qnzl-next.apk
      python tools/publish_hot.py --hot-only --apk /tmp/qnzl-next.apk

The client reads files.json from the repo's main branch (raw URL, no release
redirect involved) and downloads blobs from the fixed `hot-pool` release.
`--out-dir DIR` writes files.json + pool/ locally instead of touching GitHub
(used by the emulator end-to-end test with a local HTTP server).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FILES_JSON = REPO_ROOT / "files.json"
BASELINE_JSON = REPO_ROOT / "baseline-assets.json"
POOL_TAG = "hot-pool"
EMBEDDED_ASSET = "assets/embedded-assets.json"
POOL_GROUPS = ("content", "overlay", "protocol")

GH_CANDIDATES = [
    shutil.which("gh"),
    r"C:\Program Files\GitHub CLI\gh.exe",
]


def gh_exe() -> str:
    for candidate in GH_CANDIDATES:
        if candidate and Path(candidate).exists():
            return str(candidate)
    raise SystemExit("gh CLI not found")


def run(args: list[str]) -> str:
    result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise SystemExit(f"command failed: {' '.join(args)}\n{result.stderr or result.stdout}")
    return result.stdout


def read_manifest_from_apk(apk: Path) -> dict:
    with zipfile.ZipFile(apk) as zf:
        return json.loads(zf.read(EMBEDDED_ASSET).decode("utf-8"))


def build_files_document(apk: Path, base_version: str) -> tuple[dict, dict[str, bytes]]:
    """Return (files.json document, {sha256: blob bytes for pool upload})."""
    manifest = read_manifest_from_apk(apk)
    files = []
    blobs: dict[str, bytes] = {}
    with zipfile.ZipFile(apk) as zf:
        for row in manifest["files"]:
            if row["group"] not in POOL_GROUPS:
                continue
            data = zf.read("assets/" + row["asset"])
            digest = hashlib.sha256(data).hexdigest()
            if digest != row["sha256"]:
                raise SystemExit(
                    f"APK bytes disagree with embedded manifest for {row['asset']}"
                )
            files.append({
                "group": row["group"],
                "path": row["path"],
                "size": row["size"],
                "sha256": digest,
            })
            blobs[digest] = data
    files.sort(key=lambda f: (f["group"], f["path"]))
    document = {"baseManifest": base_version, "files": files}
    return document, blobs


def load_previous_files() -> dict | None:
    if not FILES_JSON.exists():
        return None
    try:
        return json.loads(FILES_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def changed_hashes(document: dict, previous: dict | None) -> set[str]:
    """Blobs the pool must carry: everything differing from the baseline APK,
    plus anything that ever differed earlier and is still live."""
    current = {f["path"]: f["sha256"] for f in document["files"] if f["group"] == "overlay"}
    # Blobs needed = any file whose target bytes differ from the baseline
    # embedded bytes.  The baseline is what an untouched device holds.
    needed: set[str] = set()
    baseline = json.loads(BASELINE_JSON.read_text(encoding="utf-8")) if BASELINE_JSON.exists() else None
    baseline_by_asset: dict[str, str] = {}
    if baseline:
        for row in baseline.get("files", []):
            baseline_by_asset[row["asset"]] = row["sha256"]
    for f in document["files"]:
        asset_path = f"{f['group']}/{f['path']}"
        if baseline_by_asset.get(asset_path) != f["sha256"]:
            needed.add(f["sha256"])
    return needed


def publish_local(document: dict, blobs: dict[str, bytes], needed: set[str], out_dir: Path) -> None:
    pool = out_dir / "pool"
    pool.mkdir(parents=True, exist_ok=True)
    for digest in sorted(needed):
        (pool / f"f_{digest}").write_bytes(blobs[digest])
    (out_dir / "files.json").write_text(
        json.dumps(document, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"local publish: files.json + {len(needed)} pool blob(s) -> {out_dir}")


def publish_github(document: dict, blobs: dict[str, bytes], needed: set[str]) -> None:
    gh = gh_exe()
    probe = subprocess.run(
        [gh, "release", "view", POOL_TAG, "--json", "assets"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if probe.returncode != 0:
        run([gh, "release", "create", POOL_TAG, "--title", "热更新文件池",
             "--notes", "热更新按内容寻址的文件池；由 publish_hot.py 自动维护，请勿删除。",
             "--latest=false"])
        existing: set[str] = set()
    else:
        existing = {a["name"] for a in json.loads(probe.stdout)["assets"]}
    with tempfile.TemporaryDirectory() as tmp:
        for digest in sorted(needed):
            name = f"f_{digest}"
            if name in existing:
                continue
            blob = Path(tmp) / name
            blob.write_bytes(blobs[digest])
            run([gh, "release", "upload", POOL_TAG, str(blob), "--clobber"])
            print(f"pool + {name}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apk", required=True,
                        help="locally built APK supplying the desired bytes")
    parser.add_argument("--hot-only", action="store_true",
                        help="publish only the hot channel (no APK release)")
    parser.add_argument("--out-dir", default="",
                        help="write files.json + pool/ to this directory instead of GitHub")
    args = parser.parse_args()

    apk = Path(args.apk)
    if not apk.is_file():
        raise SystemExit(f"APK not found: {apk}")

    if args.hot_only:
        if not BASELINE_JSON.exists():
            raise SystemExit("baseline-assets.json missing; publish a full release first")
        base_version = json.loads(BASELINE_JSON.read_text(encoding="utf-8"))["version"]
    else:
        manifest = read_manifest_from_apk(apk)
        base_version = manifest["version"]
        BASELINE_JSON.write_text(
            json.dumps(manifest, ensure_ascii=False) + "\n", encoding="utf-8")

    document, blobs = build_files_document(apk, base_version)
    previous = load_previous_files()
    if previous == document and not args.out_dir:
        print("hot channel unchanged; nothing to publish")
        return

    needed = changed_hashes(document, previous)
    if args.out_dir:
        publish_local(document, blobs, needed | ({f["sha256"] for f in document["files"]}
                                                 if not BASELINE_JSON.exists() else set()),
                      Path(args.out_dir))
    else:
        publish_github(document, blobs, needed)
        FILES_JSON.write_text(
            json.dumps(document, ensure_ascii=False) + "\n", encoding="utf-8")
        run(["git", "-C", str(REPO_ROOT), "add", "files.json",
             "baseline-assets.json"])
        run(["git", "-C", str(REPO_ROOT), "commit", "-m",
             f"hot channel: baseline {base_version[:12]} ({len(document['files'])} files)"])
        run(["git", "-C", str(REPO_ROOT), "push"])
        print(f"hot channel published: {len(needed)} blob(s) staged, files.json pushed")


if __name__ == "__main__":
    main()
