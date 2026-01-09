#!/usr/bin/env python3

"""
 _______                      _____           _     _                      _   _
|__   __|                    |  __ \         | |   | |                    | | (_)
   | |_ __ _   _  ___        | |__) | __ ___ | |__ | | ___ _ __ ___   __ _| |_ _  ___
   | | '__| | | |/ _ \       |  ___/ '__/ _ \| '_ \| |/ _ \ '_ ` _ \ / _` | __| |/ __|
   | | |  | |_| |  __/       | |   | | | (_) | |_) | |  __/ | | | | | (_| | |_| | (__
   |_|_|   \__,_|\___|       |_|   |_|  \___/|_.__/|_|\___|_| |_| |_|\__,_|\__|_|\___|

"""

from __future__ import annotations

import csv
import os
import re
import secrets
import shutil
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple


def _fatal_missing(dep_name: str, pip_name: str) -> None:
    print(f"\nERROR: Required library '{dep_name}' is not installed.\n\n"
          f"Install it with:\n\n"
          f"  python -m pip install {pip_name}\n", file=sys.stderr)
    print("or\n")
    print(f"  python3 -m pip install {pip_name}\n", file=sys.stderr)
    raise SystemExit(1)


try:
    from bs4 import BeautifulSoup  # type: ignore
except Exception:
    _fatal_missing("bs4 (BeautifulSoup)", "beautifulsoup4")

try:
    from gtts import gTTS  # type: ignore
except Exception:
    _fatal_missing("gTTS", "gTTS")

try:
    from pykakasi import kakasi as pykakasi_kakasi  # type: ignore
except Exception:
    _fatal_missing("pykakasi", "pykakasi")


JP_CHAR_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]+")
WHITESPACE_RE = re.compile(r"\s+")
SAFE_CHARS_RE = re.compile(r"[^a-zA-Z0-9_]+")


def build_japanese_romanizer():
    """
    Returns a function that romanizes Japanese text.
    Uses pykakasi classic API for best compatibility.
    """
    kks = pykakasi_kakasi()
    try:
        kks.setMode("H", "a")  # Hiragana to ascii
        kks.setMode("K", "a")  # Katakana to ascii
        kks.setMode("J", "a")  # Kanji to ascii
        kks.setMode("r", "Hepburn")
        kks.setMode("s", True)  # add spaces
        conv = kks.getConverter()

        def romanize_jp(text: str) -> str:
            return conv.do(text)

        return romanize_jp
    except Exception:
        try:
            kks = pykakasi_kakasi.Kakasi()  # type: ignore[attr-defined]

            def romanize_jp(text: str) -> str:
                parts = kks.convert(text)
                return " ".join(p.get("hepburn", "") for p in parts).strip()

            return romanize_jp
        except Exception as e:
            print(f"ERROR: pykakasi is installed but could not be initialized: {e}", file=sys.stderr)
            raise SystemExit(1)


ROMANIZE_JP = build_japanese_romanizer()


def contains_japanese(text: str) -> bool:
    return bool(JP_CHAR_RE.search(text))


def romanize_only_japanese(text: str) -> str:
    """
    Replaces Japanese character runs with Hepburn romanization.
    Non Japanese text is left unchanged.
    """
    def repl(match: re.Match) -> str:
        jp = match.group(0)
        rom = ROMANIZE_JP(jp)
        return rom

    return JP_CHAR_RE.sub(repl, text)


def slugify_for_filename(text: str, max_len: int = 60) -> str:
    """
    Makes a safe-ish ASCII slug.
    """
    text = romanize_only_japanese(text)
    text = text.strip()
    text = WHITESPACE_RE.sub("_", text)
    text = SAFE_CHARS_RE.sub("", text)
    text = text.strip("_")
    if not text:
        text = "audio"
    if len(text) > max_len:
        text = text[:max_len].rstrip("_")
        if not text:
            text = "audio"
    return text


def extract_first_h1_text(html: str) -> Optional[str]:
    try:
        soup = BeautifulSoup(html, "html.parser")
        h1 = soup.find("h1")
        if not h1:
            return None
        txt = h1.get_text(" ", strip=True)
        return txt if txt else None
    except Exception:
        return None


def choose_tts_lang(text: str) -> str:
    """
    Heuristic:
    If any Japanese chars exist, use Japanese TTS, else English TTS.
    """
    return "ja" if contains_japanese(text) else "en"


def make_unique_audio_filename(h1_text: str, media_dir: Path) -> str:
    base = slugify_for_filename(h1_text)
    while True:
        token = secrets.token_hex(2)  # 4 hex chars
        name = f"LLJ_{base}_{token}.mp3"
        if not (media_dir / name).exists():
            return name


def append_sound_tag(field_html: str, mp3_name: str) -> str:
    """
    Appends an Anki sound tag at the end of the field.
    Avoids duplicating if a [sound:...] already exists.
    """
    if "[sound:" in field_html:
        return field_html

    field_html = field_html.rstrip()
    # Use <br> to keep it visually separate in Anki.
    return f"{field_html}<br>[sound:{mp3_name}]"


def generate_mp3(text: str, lang: str, out_path: Path) -> None:
    """
    Generates an MP3 using gTTS.
    """
    clean = " ".join(text.split()).strip()
    if not clean:
        raise ValueError("Empty text after cleaning")

    try:
        tts = gTTS(text=clean, lang=lang)
        tts.save(str(out_path))
    except Exception as e:
        raise RuntimeError(f"TTS failed for lang={lang}: {e}") from e


def process_csv(csv_path: Path, media_dir: Path, cache: Dict[Tuple[str, str], str]) -> Tuple[int, int, int]:
    """
    Returns (rows_processed, audio_created, fields_modified)
    """
    rows_processed = 0
    audio_created = 0
    fields_modified = 0

    backup_path = csv_path.with_suffix(csv_path.suffix + ".bak")
    if not backup_path.exists():
        shutil.copy2(csv_path, backup_path)

    tmp_path = csv_path.with_suffix(csv_path.suffix + ".tmp")

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f_in, tmp_path.open("w", encoding="utf-8", newline="") as f_out:
        reader = csv.reader(f_in, delimiter=",", quotechar='"', doublequote=True)
        writer = csv.writer(
            f_out,
            delimiter=",",
            quotechar='"',
            quoting=csv.QUOTE_ALL,
            lineterminator="\n",
            doublequote=True,
        )

        for row in reader:
            rows_processed += 1

            if len(row) < 2:
                writer.writerow(row)
                continue

            front_html = row[0]
            back_html = row[1]

            front_h1 = extract_first_h1_text(front_html)
            back_h1 = extract_first_h1_text(back_html)

            # Front side
            if front_h1:
                lang = choose_tts_lang(front_h1)
                key = (front_h1, lang)
                if key in cache:
                    mp3_name = cache[key]
                else:
                    mp3_name = make_unique_audio_filename(front_h1, media_dir)
                    out_path = media_dir / mp3_name
                    generate_mp3(front_h1, lang, out_path)
                    cache[key] = mp3_name
                    audio_created += 1

                new_front = append_sound_tag(front_html, mp3_name)
                if new_front != front_html:
                    front_html = new_front
                    fields_modified += 1

            # Back side
            if back_h1:
                lang = choose_tts_lang(back_h1)
                key = (back_h1, lang)
                if key in cache:
                    mp3_name = cache[key]
                else:
                    mp3_name = make_unique_audio_filename(back_h1, media_dir)
                    out_path = media_dir / mp3_name
                    generate_mp3(back_h1, lang, out_path)
                    cache[key] = mp3_name
                    audio_created += 1

                new_back = append_sound_tag(back_html, mp3_name)
                if new_back != back_html:
                    back_html = new_back
                    fields_modified += 1

            row[0] = front_html
            row[1] = back_html
            writer.writerow(row)

    tmp_path.replace(csv_path)
    return rows_processed, audio_created, fields_modified


def main() -> int:
    base_dir = Path(__file__).resolve().parent
    media_dir = base_dir / "Media"
    media_dir.mkdir(exist_ok=True)

    csv_files = sorted([p for p in base_dir.glob("*.csv") if p.is_file()])

    if not csv_files:
        print("No CSV files found next to generateAudio.py")
        print(f"Looked in: {base_dir}")
        return 0

    print(f"Found {len(csv_files)} CSV file(s).")
    print(f"Media folder: {media_dir}")

    cache: Dict[Tuple[str, str], str] = {}

    total_rows = 0
    total_audio = 0
    total_modified = 0

    for csv_path in csv_files:
        print(f"\nProcessing: {csv_path.name}")
        try:
            rows, audio, modified = process_csv(csv_path, media_dir, cache)
            total_rows += rows
            total_audio += audio
            total_modified += modified
            print(f"  Rows read: {rows}")
            print(f"  New MP3 created: {audio}")
            print(f"  Fields modified: {modified}")
            print(f"  Backup created: {csv_path.name}.bak (only created once)")
        except Exception as e:
            print(f"ERROR while processing {csv_path.name}: {e}", file=sys.stderr)

    print("\nDone.")
    print(f"Total rows read: {total_rows}")
    print(f"Total new MP3 created: {total_audio}")
    print(f"Total fields modified: {total_modified}")
    print("\nIf MP3 creation failed, verify you have internet access and that Google TTS is reachable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
