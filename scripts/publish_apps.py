#!/usr/bin/env python3
"""Publish actual APK versions; retain historical downloads as prereleases."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

APK = re.compile(r"^(.+)-v(\d[^/]*)-(all|arm64-v8a|arm-v7a|x86_64|x86)\.apk$")
LABELS = {"googlephotos-devanced": "GooglePhotos", "youtube-morphe": "YouTube-Morphe",
          "music-morphe": "Music-Morphe", "reddit-morphe": "Reddit-Morphe",
          "twitter-piko": "Twitter"}


def identify(name):
    match = APK.fullmatch(name)
    return (match[1], match[2]) if match else None


def gh(*args):
    return subprocess.check_output(["gh", *args], text=True)


def releases(repo):
    pages = json.loads(gh("api", "--paginate", "--slurp",
                         f"repos/{repo}/releases?per_page=100"))
    return [r for page in pages for r in page if not r["draft"]]


def latest_assets(items):
    # Numeric tags remain the build history, even after being marked prerelease.
    builds = sorted((r for r in items if r["tag_name"].isdigit()),
                    key=lambda r: int(r["tag_name"]), reverse=True)
    selected = {}
    result = []
    for release in builds:
        for asset in release["assets"]:
            key = identify(asset["name"])
            if key is None or key[0] not in LABELS:
                continue
            app, version = key
            selected.setdefault(app, (version, release["tag_name"]))
            if selected[app] == (version, release["tag_name"]):
                result.append((release["tag_name"], asset["name"]))
    return result


def backfill(directory, repo):
    for tag, name in latest_assets(releases(repo)):
        gh("release", "download", tag, "--repo", repo,
           "--pattern", name, "--dir", str(directory))


def publish(directory, repo):
    groups = {}
    for apk in sorted(Path(directory).glob("*.apk")):
        key = identify(apk.name)
        if key is None or key[0] not in LABELS:
            raise ValueError(f"Unexpected APK name: {apk.name}")
        groups.setdefault(key[1], []).append(apk)
    existing = {r["tag_name"]: r for r in releases(repo)}
    for version, files in groups.items():
        names = {identify(p.name)[0] for p in files}
        notes = "\n".join(f"{LABELS[app]}: {version}  " for app in sorted(names))
        notes += "\n\n" + " ".join(sorted(names))
        notes += "\n\nThe release tag is the application version. APKs retain their original signatures."
        if version in existing:
            release = existing[version]
            asset_names = {a["name"] for a in release["assets"]}
            missing = [str(p) for p in files if p.name not in asset_names]
            if missing:
                gh("release", "upload", version, *missing, "--repo", repo)
            # Preserve notes of any other app sharing this exact version tag.
            old_notes = release.get("body") or ""
            if any(LABELS[app] not in old_notes for app in names):
                gh("release", "edit", version, "--repo", repo,
                   "--notes", old_notes + "\n\n" + notes)
        else:
            gh("release", "create", version, *(str(p) for p in files),
               "--repo", repo, "--title", f"Release {version}",
               "--latest=false", "--notes", notes)


def reconcile_history(repo):
    items = releases(repo)
    expected = latest_assets(items)
    covered_apps = {identify(name)[0] for _, name in expected}
    if covered_apps != set(LABELS):
        raise RuntimeError("Missing app build history; refusing to change release visibility")
    keep = {identify(name)[1] for _, name in expected}
    by_tag = {r["tag_name"]: r for r in items}
    for _, name in expected:
        version = identify(name)[1]
        if version not in by_tag or name not in {a["name"] for a in by_tag[version]["assets"]}:
            raise RuntimeError(f"Missing canonical APK {name}; retaining historical releases")
    # Only change metadata after every current app/architecture is available.
    for release in items:
        tag = release["tag_name"]
        if tag in keep:
            if release["prerelease"]:
                gh("release", "edit", tag, "--repo", repo,
                   "--prerelease=false", "--latest=false")
        elif not release["prerelease"]:
            gh("release", "edit", tag, "--repo", repo,
               "--prerelease", "--latest=false")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", nargs="?", default="build")
    parser.add_argument("--backfill", action="store_true")
    parser.add_argument("--migrate-history", action="store_true",
                        help="Retire legacy stable tags only after validating existing client migration")
    args = parser.parse_args()
    repo = os.environ["GITHUB_REPOSITORY"]
    if args.backfill:
        with tempfile.TemporaryDirectory() as directory:
            backfill(directory, repo)
            publish(directory, repo)
    else:
        publish(args.directory, repo)
    if args.migrate_history:
        reconcile_history(repo)


if __name__ == "__main__":
    main()
