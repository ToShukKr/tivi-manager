#!/usr/bin/env python3
"""
TiVi Manager

Usage:
    python manager.py --kp_id 12345
    python manager.py --kp_id 12345 --bucket tivi_db --quality 720 --translation 1
    python manager.py --kp_id 12345 --dry-run

Workflow:
    1) Receive --kp_id
    2) Fetch metadata (seasons/episodes or movie) from the provider (collaps)
    3) Compare with what's already in the archive.org bucket
    4) Download + upload any missing episodes/movie
    5) Report if everything is already present
"""

import os
import sys
import re
import json
import argparse
import logging
import tempfile

# Make bin/ importable
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin"))

from collaps import ProviderAPI, get_metadata
from archive import Archive


def setup_logger(name="tivi"):
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        logger.addHandler(handler)
    return logger


logger = setup_logger("tivi")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_expected_files(metadata):
    """
    Build a dict of expected remote files.

    Returns:
        {"type": "serial"|"movie", "expected": {"s-e": {"season","episode","title"}}}
    """
    result = metadata.get("result", {})
    content_type = result.get("type", "movie")
    expected = {}

    if content_type == "serial":
        episodes_map = result.get("episodes", {})
        for season_str, episodes in episodes_map.items():
            season = int(season_str)
            for episode_str, title in episodes.items():
                episode = int(episode_str)
                key = f"{season}-{episode}"
                expected[key] = {"season": season, "episode": episode, "title": title}
    else:
        expected["0-0"] = {"season": 0, "episode": 0, "title": "Movie"}

    return {"type": content_type, "expected": expected}


def get_bucket_files(archive, bucket, kp_id):
    """
    Return a set of (season, episode) tuples already in the bucket under <kp_id>/.
    """
    try:
        raw = archive.get_kp_id_files(bucket, kp_id)
        data = json.loads(raw)
    except FileNotFoundError:
        return set()
    except Exception as e:
        logger.warning(f"Could not list bucket files: {e}")
        return set()

    found = set()
    prefix = f"{kp_id}-"
    for f in data.get("files", []):
        name = f.get("name", "")
        basename = name.split("/")[-1]
        if not basename.endswith(".dat"):
            continue
        stem = basename[:-4]
        if not stem.startswith(prefix):
            continue
        stem = stem[len(prefix):]
        m = re.match(r"(\d+)-(\d+)-", stem)
        if m:
            found.add((int(m.group(1)), int(m.group(2))))
    return found


def get_local_files(download_dir, kp_id):
    """
    Return a dict of (season, episode) -> file_path for files already in download_dir.
    """
    found = {}
    if not os.path.exists(download_dir):
        return found

    for filename in os.listdir(download_dir):
        if not filename.endswith(".mp4"):
            continue
        stem = filename[:-4]
        m = re.match(rf"{kp_id}-(\d+)-(\d+)-", stem)
        if m:
            season, episode = int(m.group(1)), int(m.group(2))
            file_path = os.path.join(download_dir, filename)
            if os.path.getsize(file_path) > 0:
                found[(season, episode)] = file_path
    return found


def download_episode(collaps, kp_id, season, episode, quality, translation,
                     download_dir, verbose=False):
    """Download a single episode/movie and return the file path."""
    if collaps.contentType == 'serial':
        master = collaps.getStream(season, episode)
    else:
        master = collaps.getMovie()

    if not master:
        logger.error(f"Could not get stream for S{season}E{episode}")
        return None

    video_url, audio_url, chosen = collaps.getLink(master, quality=quality,
                                                   translation=translation)

    duration = ""
    try:
        import requests
        r = requests.get(video_url, headers=collaps.HEADERS, timeout=30)
        durations = re.findall(r'#EXTINF:([0-9.]+)', r.text)
        duration = str(int(sum(float(d) for d in durations)))
    except Exception:
        pass

    translation_name = chosen.split(" / ", 1)[1] if " / " in chosen else "default"
    audios, _ = collaps._parse(master)
    translation_code = "default"
    for audio in audios:
        if audio["name"] == translation_name:
            translation_code = audio["code"]
            break

    if collaps.contentType == 'serial':
        filename = f"{kp_id}-{season}-{episode}-{duration}-{translation_code}.mp4"
    else:
        filename = f"{kp_id}-0-0-{duration}-{translation_code}.mp4"

    output_path = os.path.join(download_dir, filename)
    collaps.getFile(master, output=output_path, quality=quality,
                    translation=translation, verbose=verbose)
    return output_path


# ---------------------------------------------------------------------------
# Helper: metadata caching
# ---------------------------------------------------------------------------

def get_or_fetch_metadata(kp_id, bucket, archive, dry_run):
    """
    Try to get metadata from bucket cache.
    If not present or failed to load, fetch from collaps, cache (unless dry_run), and return.
    Returns (metadata, collaps) where collaps is a ProviderAPI instance.
    """
    # Try to download cached metadata
    metadata_json_path = os.path.join(tempfile.gettempdir(), f"{kp_id}_metadata.json")
    if archive.download_file(bucket, f"{kp_id}/metadata.json", metadata_json_path):
        try:
            with open(metadata_json_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            logger.info(f"Using cached metadata for kp_id={kp_id} from bucket.")
            # We still need to create collaps instance for later use.
            collaps = ProviderAPI(kp_id)
            return metadata, collaps
        except Exception as e:
            logger.warning(f"Failed to load cached metadata: {e}")
    # Fetch from collaps
    collaps = ProviderAPI(kp_id)
    metadata = get_metadata(collaps)
    # Cache it unless dry_run
    if not dry_run:
        # Write metadata to temp file
        with open(metadata_json_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        # Upload to bucket
        logger.info(f"Caching metadata for kp_id={kp_id} to bucket.")
        upload_success = archive.upload(metadata_json_path, bucket, remote_name=f"{kp_id}/metadata.json")
        # Clean up the temporary file
        try:
            os.remove(metadata_json_path)
        except OSError as e:
            logger.warning(f"Failed to remove temporary metadata file {metadata_json_path}: {e}")
        if not upload_success:
            logger.error(f"Failed to upload metadata for kp_id={kp_id}.")
        # Clean up temp file? We'll leave it; it's in temp directory.
    else:
        logger.info(f"Dry run: not caching metadata to bucket.")
    return metadata, collaps


# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------

def run(kp_id, bucket, quality, translation, download_dir, dry_run, verbose):
    logger.info(f"=== TiVi Manager: kp_id={kp_id}, bucket={bucket} ===")

    # 0) Setup archive
    archive = Archive()
    logger.info(f"Checking bucket '{bucket}' for existing files...")
    bucket_files = get_bucket_files(archive, bucket, kp_id)
    logger.info(f"Checking local directory '{download_dir}' for existing files...")
    local_files = get_local_files(download_dir, kp_id)

    # 1) Fetch metadata (with caching)
    logger.info("Fetching metadata from provider (with caching)...")
    metadata, collaps = get_or_fetch_metadata(kp_id, bucket, archive, dry_run)
    content_type = metadata.get("result", {}).get("type", "movie")
    title = metadata.get("result", {}).get("name", "Unknown")
    logger.info(f"Title: {title}  |  Type: {content_type}")

    # 2) Build expected list
    expected_info = get_expected_files(metadata)
    expected = expected_info["expected"]
    logger.info(f"Expected files: {len(expected)}")

    # 3) Determine what's missing
    missing, present = [], []
    for key, info in sorted(expected.items()):
        s, e = info["season"], info["episode"]
        if (s, e) in bucket_files:
            present.append((s, e, info["title"], "bucket"))
        elif (s, e) in local_files:
            present.append((s, e, info["title"], "local"))
        else:
            missing.append((s, e, info["title"]))

    if present:
        logger.info(f"Already present ({len(present)}):")
        for s, e, t, src in present:
            label = f"S{s:02d}E{e:02d}" if content_type == "serial" else "Movie"
            marker = "✓" if src == "bucket" else "📁"
            logger.info(f"  {marker} {label} — {t} [{src}]")

    if not missing:
        logger.info("✅ All episodes/movie are already present. Nothing to do.")
        return

    logger.info(f"Missing ({len(missing)}):")
    for s, e, t in missing:
        label = f"S{s:02d}E{e:02d}" if content_type == "serial" else "Movie"
        logger.info(f"  ✗ {label} — {t}")

    if dry_run:
        logger.info("--dry-run is set, skipping download/upload.")
        return

    # 4) Download + upload missing
    os.makedirs(download_dir, exist_ok=True)
    total = len(missing)
    for i, (season, episode, ep_title) in enumerate(missing, 1):
        label = f"S{season:02d}E{episode:02d}" if content_type == "serial" else "Movie"
        logger.info(f"[{i}/{total}] Processing {label} — {ep_title}")

        # Check if file exists locally (might have been downloaded but not uploaded)
        if (season, episode) in local_files:
            file_path = local_files[(season, episode)]
            logger.info(f"  Found local file: {os.path.basename(file_path)}, skipping download.")
        else:
            logger.info(f"  Downloading {label}...")
            file_path = download_episode(collaps, kp_id, season, episode,
                                         quality, translation, download_dir, verbose)
            if not file_path or not os.path.exists(file_path):
                logger.error(f"  Download failed for {label}, skipping.")
                continue

        logger.info(f"  Uploading {label} to bucket...")
        archive.upload_video(file=file_path, bucket=bucket, kp_id=kp_id)
        logger.info(f"  ✓ {label} uploaded successfully.")

    logger.info("=== Done ===")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="TiVi Manager")
    parser.add_argument("--kp-id", required=True,
                        help="Kinopoisk ID of the movie/series")
    parser.add_argument("--bucket", default="tivi_db",
                        help="Destination archive.org bucket (default: tivi_db)")
    parser.add_argument("--quality", default=None,
                        help="Max quality height, e.g. 720, 1080 (default: best)")
    parser.add_argument("--translation", default=None,
                        help="Translation ID or name (default: first available)")
    parser.add_argument("--download_dir", default="/tmp/tivi_downloads",
                        help="Temp dir for downloaded files")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be done without downloading/uploading")
    parser.add_argument("--verbose", action="store_true",
                        help="Show ffmpeg output")
    return parser.parse_args()


def main():
    args = parse_args()
    run(
        kp_id=args.kp_id,
        bucket=args.bucket,
        quality=args.quality,
        translation=args.translation,
        download_dir=args.download_dir,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    main()