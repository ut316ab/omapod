#!/usr/bin/env python3
"""
NASA Astronomy Picture of the Day (APOD) backend script for Omarchy status bar plugin.
Handles API fetching, local disk caching, image downloads, wallpaper application,
and image export.
"""

import sys
import os
import json
import argparse
import datetime
import random
import re
import urllib.request
import urllib.parse
import subprocess
import shutil
import html
from pathlib import Path

# Directories
CACHE_DIR = Path.home() / ".cache" / "omarchy-omapod"
IMAGES_DIR = CACHE_DIR / "images"
PICTURES_DIR = Path.home() / "Pictures" / "NASA_APOD"
STATE_FILE = CACHE_DIR / "state.json"

CACHE_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
PICTURES_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_API_KEY = "DEMO_KEY"
APOD_API_URL = "https://api.nasa.gov/planetary/apod"
FIRST_APOD_DATE = datetime.date(1995, 6, 16)


def get_today_date() -> datetime.date:
    """Return current date in UTC/local."""
    return datetime.date.today()


def date_to_web_url(dt: datetime.date) -> str:
    """Construct official NASA APOD archive web page URL: apYYMMDD.html"""
    yy = dt.strftime("%y")
    mm = dt.strftime("%m")
    dd = dt.strftime("%d")
    return f"https://apod.nasa.gov/apod/ap{yy}{mm}{dd}.html"


def send_notification(title: str, message: str, icon: str = "astronomy"):
    """Send desktop notification via Omarchy notification tool or notify-send."""
    omarchy_bin = os.environ.get("OMARCHY_PATH", "/usr/share/omarchy") + "/bin/omarchy-notification-send"
    if os.path.exists(omarchy_bin):
        try:
            subprocess.run([omarchy_bin, title, message], check=False)
            return
        except Exception:
            pass

    if shutil.which("notify-send"):
        try:
            subprocess.run(["notify-send", "-a", "NASA APOD", title, message], check=False)
        except Exception:
            pass


def download_file(url: str, dest_path: Path, timeout: int = 30) -> bool:
    """Download a file with User-Agent header and save to destination."""
    if not url:
        return False
    if dest_path.exists() and dest_path.stat().st_size > 0:
        return True

    temp_path = dest_path.with_suffix(dest_path.suffix + ".tmp")
    headers = {"User-Agent": "Omarchy-NASA-APOD-Plugin/1.0"}
    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            with open(temp_path, "wb") as out_file:
                shutil.copyfileobj(response, out_file)
        temp_path.rename(dest_path)
        return True
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        print(f"Error downloading {url}: {e}", file=sys.stderr)
        return False


def create_fallback_svg(title: str, date_str: str, dest_path: Path) -> bool:
    """Generate a clean vector space illustration thumbnail for videos without thumbnail."""
    safe_title = html.escape(title[:55] + ("..." if len(title) > 55 else ""))
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="800" height="450" viewBox="0 0 800 450">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0b0d19"/>
      <stop offset="50%" stop-color="#181e3a"/>
      <stop offset="100%" stop-color="#080911"/>
    </linearGradient>
    <linearGradient id="glow" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#89b4fa" stop-opacity="0.9"/>
      <stop offset="100%" stop-color="#cba6f7" stop-opacity="0.9"/>
    </linearGradient>
  </defs>
  <rect width="100%" height="100%" fill="url(#bg)"/>
  <!-- Starfield -->
  <circle cx="120" cy="80" r="1.5" fill="#ffffff" opacity="0.6"/>
  <circle cx="240" cy="150" r="1" fill="#ffffff" opacity="0.4"/>
  <circle cx="680" cy="90" r="2" fill="#ffffff" opacity="0.7"/>
  <circle cx="520" cy="320" r="1.5" fill="#ffffff" opacity="0.5"/>
  <circle cx="350" cy="70" r="1" fill="#ffffff" opacity="0.3"/>
  <circle cx="710" cy="280" r="1.2" fill="#ffffff" opacity="0.6"/>
  <circle cx="180" cy="360" r="2" fill="#ffffff" opacity="0.8"/>
  <circle cx="420" cy="390" r="1" fill="#ffffff" opacity="0.4"/>

  <!-- Play Circle Icon -->
  <circle cx="400" cy="170" r="46" fill="url(#glow)"/>
  <polygon points="390,148 422,170 390,192" fill="#11111b"/>

  <!-- Labels -->
  <text x="400" y="260" font-family="monospace, sans-serif" font-size="20" font-weight="bold" fill="#cdd6f4" text-anchor="middle">{safe_title}</text>
  <text x="400" y="295" font-family="monospace, sans-serif" font-size="14" fill="#89b4fa" text-anchor="middle">NASA APOD • {date_str} • ASTRONOMY VIDEO</text>
  <text x="400" y="328" font-family="monospace, sans-serif" font-size="12" fill="#a6adc8" text-anchor="middle">External Video Stream / Archive</text>
</svg>"""
    try:
        with open(dest_path, "w", encoding="utf-8") as f:
            f.write(svg)
        return True
    except Exception as e:
        print(f"Error creating fallback svg: {e}", file=sys.stderr)
        return False


def extract_video_thumbnail(video_url: str, dest_path: Path, title: str = "", date_str: str = "") -> bool:
    """If media is a video (YouTube, Vimeo, MP4), extract/download thumbnail or create SVG fallback."""
    if dest_path.exists() and dest_path.stat().st_size > 0:
        return True

    # Check for YouTube URL
    yt_match = re.search(r'(?:youtube\.com/(?:embed/|watch\?v=)|youtu\.be/)([a-zA-Z0-9_-]{11})', video_url)
    if yt_match:
        yt_id = yt_match.group(1)
        for quality in ["maxresdefault.jpg", "hqdefault.jpg", "mqdefault.jpg", "default.jpg", "0.jpg"]:
            yt_thumb_url = f"https://img.youtube.com/vi/{yt_id}/{quality}"
            if download_file(yt_thumb_url, dest_path, timeout=6):
                return True

    # Check for Vimeo URL
    vimeo_match = re.search(r'(?:vimeo\.com/(?:video/)?|player\.vimeo\.com/video/)(\d+)', video_url)
    if vimeo_match:
        vimeo_id = vimeo_match.group(1)
        try:
            req = urllib.request.Request(f"https://vimeo.com/api/v2/video/{vimeo_id}.json", headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                v_data = json.loads(resp.read().decode("utf-8"))
                if v_data and isinstance(v_data, list) and len(v_data) > 0:
                    v_thumb = v_data[0].get("thumbnail_large") or v_data[0].get("thumbnail_medium")
                    if v_thumb and download_file(v_thumb, dest_path, timeout=6):
                        return True
        except Exception:
            pass

    # If direct mp4 and ffmpeg available
    if (video_url.endswith(".mp4") or ".mp4" in video_url) and shutil.which("ffmpeg"):
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-ss", "00:00:00.5", "-i", video_url, "-frames:v", "1", "-update", "1", str(dest_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=8,
            )
            if dest_path.exists() and dest_path.stat().st_size > 0:
                return True
        except Exception:
            pass

    # Fallback: create stylized space SVG thumbnail
    svg_path = dest_path.with_suffix(".svg")
    if create_fallback_svg(title or "Astronomy Video", date_str or "", svg_path):
        return True

    return False


def sanitize_filename(name: str) -> str:
    """Sanitize string for filename."""
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    name = name.replace(" ", "_").strip("._")
    return name[:60]


def fetch_apod_from_html(target_date: datetime.date) -> dict | None:
    """Fallback to scrape official NASA APOD archive HTML if API rate-limited or unavailable."""
    iso_date = target_date.strftime("%Y-%m-%d")
    yy = target_date.strftime("%y")
    mm = target_date.strftime("%m")
    dd = target_date.strftime("%d")
    page_url = f"https://apod.nasa.gov/apod/ap{yy}{mm}{dd}.html"

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    req = urllib.request.Request(page_url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"HTML fallback error for {iso_date}: {e}", file=sys.stderr)
        return None

    # Title
    title = ""
    t_match = re.search(r"<center>\s*<b>\s*(.*?)\s*</b>\s*<br>", content, re.I | re.S)
    if t_match:
        title = re.sub(r"<[^>]+>", "", t_match.group(1)).strip()
    if not title:
        t_match = re.search(r"<title>\s*APOD:[^–\-]+[–\-]\s*(.*?)\s*</title>", content, re.I | re.S)
        if t_match:
            title = re.sub(r"<[^>]+>", "", t_match.group(1)).strip()
    if not title:
        title = "Astronomy Picture of the Day"

    # Media URLs
    media_type = "image"
    media_url = ""
    hd_url = ""

    img_match = re.search(r"<a\s+href=[\"\x27](image/[^\"\x27]+)[\"\x27]>\s*<IMG\s+SRC=[\"\x27](image/[^\"\x27]+)[\"\x27]", content, re.I | re.S)
    if img_match:
        hd_rel = img_match.group(1)
        img_rel = img_match.group(2)
        hd_url = f"https://apod.nasa.gov/apod/{hd_rel}"
        media_url = f"https://apod.nasa.gov/apod/{img_rel}"
    else:
        img_match2 = re.search(r"<IMG\s+SRC=[\"\x27](image/[^\"\x27]+)[\"\x27]", content, re.I)
        if img_match2:
            img_rel = img_match2.group(1)
            media_url = f"https://apod.nasa.gov/apod/{img_rel}"
            hd_url = media_url

    if not media_url:
        vid_match = re.search(r"<iframe\s+[^>]*src=[\"\x27](https?://[^\"\x27]+)[\"\x27]", content, re.I)
        if vid_match:
            media_type = "video"
            media_url = vid_match.group(1)
            hd_url = media_url
        else:
            vid_match2 = re.search(r"<a\s+href=[\"\x27](image/[^\"\x27]+\.mp4)[\"\x27]", content, re.I)
            if vid_match2:
                media_type = "video"
                media_url = f"https://apod.nasa.gov/apod/{vid_match2.group(1)}"
                hd_url = media_url

    # Copyright / Credit
    copyright_text = ""
    c_match = re.search(r"<b>\s*(?:Image\s+Credit(?:\s*&\s*Copyright)?|Credit(?:\s*&\s*Copyright)?|Copyright|Image\s+Credit):\s*</b>\s*(.*?)\s*</center>", content, re.I | re.S)
    if c_match:
        raw_c = re.sub(r"<[^>]+>", " ", c_match.group(1))
        copyright_text = re.sub(r"\s+", " ", raw_c).strip()

    # Explanation
    explanation = ""
    e_match = re.search(r"<b>\s*Explanation:\s*</b>\s*(.*?)(?:<p>\s*<center>|<hr>|<p>\s*<table|<center>|Tomorrow\x27s\s+picture)", content, re.I | re.S)
    if e_match:
        raw_e = re.sub(r"<[^>]+>", " ", e_match.group(1))
        raw_e = html.unescape(raw_e)
        explanation = re.sub(r"\s+", " ", raw_e).strip()

    return {
        "title": title,
        "date": iso_date,
        "media_type": media_type,
        "url": media_url,
        "hdurl": hd_url or media_url,
        "thumbnail_url": "",
        "copyright": copyright_text,
        "explanation": explanation,
    }


def fetch_apod(date_str: str = None, api_key: str = None, force_refresh: bool = False) -> dict:
    """
    Fetch APOD data for a date.
    Returns normalized dictionary with paths, URLs, title, and metadata.
    """
    today = get_today_date()
    if not date_str:
        target_date = today
    else:
        try:
            target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            target_date = today

    if target_date > today:
        target_date = today
    if target_date < FIRST_APOD_DATE:
        target_date = FIRST_APOD_DATE

    iso_date = target_date.strftime("%Y-%m-%d")
    prev_dt = target_date - datetime.timedelta(days=1)
    prev_date = prev_dt.strftime("%Y-%m-%d") if prev_dt >= FIRST_APOD_DATE else None
    next_dt = target_date + datetime.timedelta(days=1)
    next_date = next_dt.strftime("%Y-%m-%d") if next_dt <= today else None

    cache_json_file = CACHE_DIR / f"apod_{iso_date}.json"
    key = api_key if api_key and api_key.strip() else DEFAULT_API_KEY

    apod_raw = None

    # Check local cache
    if not force_refresh and cache_json_file.exists():
        try:
            with open(cache_json_file, "r", encoding="utf-8") as f:
                apod_raw = json.load(f)
        except Exception:
            apod_raw = None

    # Fetch from API if not cached or force refresh
    if not apod_raw:
        params = {
            "api_key": key,
            "date": iso_date,
            "thumbs": "True",
        }
        url = f"{APOD_API_URL}?{urllib.parse.urlencode(params)}"
        headers = {"User-Agent": "Omarchy-NASA-APOD-Plugin/1.0"}
        req = urllib.request.Request(url, headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read().decode("utf-8")
                apod_raw = json.loads(data)
                # Cache raw JSON
                with open(cache_json_file, "w", encoding="utf-8") as f:
                    f.write(data)
        except Exception as e:
            # Fallback to HTML scraping
            print(f"API request failed ({e}), falling back to HTML archive...", file=sys.stderr)
            apod_raw = fetch_apod_from_html(target_date)
            if apod_raw:
                try:
                    with open(cache_json_file, "w", encoding="utf-8") as f:
                        json.dump(apod_raw, f, indent=2, ensure_ascii=False)
                except Exception:
                    pass
            else:
                return {
                    "success": False,
                    "date": iso_date,
                    "prev_date": prev_date,
                    "next_date": next_date,
                    "error": f"Failed to fetch APOD: {e}",
                }

    # Normalize fields
    title = apod_raw.get("title", "Astronomy Picture of the Day")
    explanation = apod_raw.get("explanation", "")
    copyright_text = apod_raw.get("copyright", "").strip().replace("\n", " ")
    media_type = apod_raw.get("media_type", "image")
    media_url = apod_raw.get("url", "")
    hd_url = apod_raw.get("hdurl", media_url)
    thumbnail_url = apod_raw.get("thumbnail_url", "")

    # Calculate prev & next dates
    prev_dt = target_date - datetime.timedelta(days=1)
    prev_date = prev_dt.strftime("%Y-%m-%d") if prev_dt >= FIRST_APOD_DATE else None
    next_dt = target_date + datetime.timedelta(days=1)
    next_date = next_dt.strftime("%Y-%m-%d") if next_dt <= today else None

    # Handle image download
    local_image_path = ""
    local_hd_path = ""

    if media_type == "image" and media_url:
        ext = os.path.splitext(urllib.parse.urlparse(media_url).path)[1] or ".jpg"
        clean_title = sanitize_filename(title)
        img_filename = f"{iso_date}_{clean_title}{ext}"
        img_path = IMAGES_DIR / img_filename

        if download_file(media_url, img_path):
            local_image_path = str(img_path)

        if hd_url and hd_url != media_url:
            hd_filename = f"{iso_date}_{clean_title}_hd{ext}"
            hd_path = IMAGES_DIR / hd_filename
            if hd_path.exists() and hd_path.stat().st_size > 0:
                local_hd_path = str(hd_path)

    local_video_path = ""
    if media_type == "video":
        clean_title = sanitize_filename(title)
        thumb_path = IMAGES_DIR / f"{iso_date}_{clean_title}_thumb.jpg"
        svg_thumb_path = IMAGES_DIR / f"{iso_date}_{clean_title}_thumb.svg"
        vid_file = IMAGES_DIR / f"{iso_date}_video.mp4"
        if vid_file.exists() and vid_file.stat().st_size > 0:
            local_video_path = str(vid_file)

        if thumbnail_url and download_file(thumbnail_url, thumb_path):
            local_image_path = str(thumb_path)
        elif media_url:
            extract_video_thumbnail(media_url, thumb_path, title=title, date_str=iso_date)
            if thumb_path.exists() and thumb_path.stat().st_size > 0:
                local_image_path = str(thumb_path)
            elif svg_thumb_path.exists() and svg_thumb_path.stat().st_size > 0:
                local_image_path = str(svg_thumb_path)

    state = {
        "success": True,
        "date": iso_date,
        "formatted_date": target_date.strftime("%B %d, %Y"),
        "title": title,
        "explanation": explanation,
        "copyright": copyright_text,
        "media_type": media_type,
        "url": media_url,
        "hdurl": hd_url,
        "thumbnail_url": thumbnail_url,
        "local_image": local_image_path,
        "local_hd_image": local_hd_path,
        "local_video": local_video_path,
        "web_url": date_to_web_url(target_date),
        "is_today": target_date == today,
        "prev_date": prev_date,
        "next_date": next_date,
        "error": None,
    }

    # Save to state.json
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving state: {e}", file=sys.stderr)

    return state


def get_random_date() -> str:
    """Generate random date between 1995-06-16 and today."""
    today = get_today_date()
    days_range = (today - FIRST_APOD_DATE).days
    random_days = random.randint(0, days_range)
    random_dt = FIRST_APOD_DATE + datetime.timedelta(days=random_days)
    return random_dt.strftime("%Y-%m-%d")


def download_hd_image(state: dict) -> str:
    """Download full HD image if available, return local path."""
    if not state.get("success") or state.get("media_type") != "image":
        return state.get("local_image", "")

    hd_url = state.get("hdurl") or state.get("url")
    if not hd_url:
        return state.get("local_image", "")

    iso_date = state.get("date")
    clean_title = sanitize_filename(state.get("title", "apod"))
    ext = os.path.splitext(urllib.parse.urlparse(hd_url).path)[1] or ".jpg"
    hd_path = IMAGES_DIR / f"{iso_date}_{clean_title}_hd{ext}"

    if hd_path.exists() and hd_path.stat().st_size > 0:
        return str(hd_path)

    if download_file(hd_url, hd_path, timeout=60):
        state["local_hd_image"] = str(hd_path)
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
        return str(hd_path)

    return state.get("local_image", "")


def set_as_wallpaper(prefer_hd: bool = True) -> dict:
    """Apply current APOD image as desktop background using Omarchy theme tool."""
    if not STATE_FILE.exists():
        fetch_apod()

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
    except Exception as e:
        return {"success": False, "error": f"Failed to load state: {e}"}

    if not state.get("success"):
        return {"success": False, "error": state.get("error", "No APOD loaded")}

    if state.get("media_type") != "image":
        return {"success": False, "error": "Today's APOD is a video, cannot set as wallpaper"}

    image_path = ""
    if prefer_hd:
        image_path = download_hd_image(state)
    if not image_path:
        image_path = state.get("local_image", "")

    if not image_path or not os.path.exists(image_path):
        return {"success": False, "error": "Image file not available locally"}

    # Execute `omarchy theme bg set <image_path>`
    omarchy_bin = shutil.which("omarchy")
    if not omarchy_bin and os.path.exists("/usr/share/omarchy/bin/omarchy-theme-bg-set"):
        cmd = ["/usr/share/omarchy/bin/omarchy-theme-bg-set", image_path]
    elif omarchy_bin:
        cmd = [omarchy_bin, "theme", "bg", "set", image_path]
    else:
        # Fallback to hyprctl hyprpaper if hyprpaper is running
        cmd = ["hyprctl", "hyprpaper", "wallpaper", f",{image_path}"]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if res.returncode == 0:
            title = state.get("title", "NASA APOD")
            send_notification("Wallpaper Updated", f"NASA APOD: {title}")
            return {"success": True, "image_path": image_path, "title": title}
        else:
            return {"success": False, "error": f"Wallpaper command failed: {res.stderr}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def save_image_to_pictures() -> dict:
    """Save/copy HD image to ~/Pictures/NASA_APOD/"""
    if not STATE_FILE.exists():
        fetch_apod()

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
    except Exception as e:
        return {"success": False, "error": str(e)}

    if not state.get("success") or state.get("media_type") != "image":
        return {"success": False, "error": "No image APOD loaded"}

    image_path = download_hd_image(state) or state.get("local_image", "")
    if not image_path or not os.path.exists(image_path):
        return {"success": False, "error": "Image not found"}

    iso_date = state.get("date", "apod")
    clean_title = sanitize_filename(state.get("title", "image"))
    ext = os.path.splitext(image_path)[1] or ".jpg"
    dest_file = PICTURES_DIR / f"NASA_APOD_{iso_date}_{clean_title}{ext}"

    try:
        shutil.copy2(image_path, dest_file)
        send_notification("Image Saved", f"Saved to ~/Pictures/NASA_APOD/{dest_file.name}")
        return {"success": True, "saved_path": str(dest_file)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def copy_to_clipboard(kind: str = "image") -> dict:
    """Copy APOD image directly to clipboard via wl-copy (or URL as fallback)."""
    if not STATE_FILE.exists():
        fetch_apod()

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
    except Exception as e:
        return {"success": False, "error": str(e)}

    # If user wants to copy image
    if kind == "image":
        image_path = state.get("local_hd_image") or state.get("local_image")
        if not image_path or not os.path.exists(image_path):
            image_path = download_hd_image(state) or state.get("local_image")

        if image_path and os.path.exists(image_path):
            ext = os.path.splitext(image_path)[1].lower()
            mime_type = "image/png" if ext == ".png" else "image/jpeg"
            if shutil.which("wl-copy"):
                try:
                    with open(image_path, "rb") as f:
                        subprocess.run(["wl-copy", "--type", mime_type], input=f.read(), check=True)
                    title = state.get("title", "NASA APOD")
                    send_notification("Image Copied", f"Copied image: {title}")
                    return {"success": True, "copied": "image", "path": image_path}
                except Exception as e:
                    print(f"wl-copy image error: {e}", file=sys.stderr)

    # Fallback / Link copy
    if kind == "hd":
        url = state.get("hdurl") or state.get("url", "")
    elif kind == "media":
        url = state.get("url", "")
    else:
        url = state.get("web_url") or state.get("url", "")

    if not url:
        return {"success": False, "error": "No URL available"}

    if shutil.which("wl-copy"):
        try:
            subprocess.run(["wl-copy", url], check=True)
            send_notification("Link Copied", f"Copied {url} to clipboard")
            return {"success": True, "copied": "url", "url": url}
        except Exception as e:
            return {"success": False, "error": str(e)}
    else:
        return {"success": False, "error": "wl-copy not installed"}


def normalize_video_url(url: str) -> str:
    """Normalize YouTube embed/short URLs to standard watch URLs for MPV/yt-dlp."""
    if not url:
        return ""
    yt_match = re.search(r'(?:youtube\.com/(?:embed/|watch\?v=)|youtu\.be/)([a-zA-Z0-9_-]{11})', url)
    if yt_match:
        return f"https://www.youtube.com/watch?v={yt_match.group(1)}"
    return url


def probe_video_playable(url: str) -> tuple[bool, str]:
    """Check if stream is playable with yt-dlp/mpv, returning (is_playable, reason)."""
    if not url:
        return False, "No URL"
    if url.endswith(".mp4") or ".mp4" in url:
        return True, ""

    # Probe with yt-dlp if available
    if shutil.which("yt-dlp"):
        try:
            res = subprocess.run(
                ["yt-dlp", "--simulate", "--quiet", "--no-warnings", "--no-playlist", url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                timeout=4,
            )
            if res.returncode == 0:
                return True, ""
            err = res.stderr.lower()
            if "private video" in err:
                return False, "Video is private on YouTube"
            if "removed" in err or "deleted" in err:
                return False, "Video was removed from YouTube"
            if "unavailable" in err:
                return False, "Video is unavailable"
        except Exception:
            pass
    return True, ""


def play_media() -> dict:
    """Play video in MPV player or default video player/browser with robust fallback."""
    if not STATE_FILE.exists():
        fetch_apod()

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
    except Exception as e:
        return {"success": False, "error": f"Failed to load state: {e}"}

    media_type = state.get("media_type", "image")
    media_url = state.get("url")
    title = state.get("title", "NASA APOD")

    if not media_url:
        return {"success": False, "error": "No media URL available"}

    if media_type == "video":
        norm_url = normalize_video_url(media_url)
        is_playable, reason = probe_video_playable(norm_url)

        if not is_playable:
            send_notification("Video Unavailable on YouTube", f"{reason}. Opening NASA APOD archive page...")
            return open_in_browser(prefer_video_url=False)

        if shutil.which("mpv"):
            try:
                cmd = [
                    "mpv",
                    "--autofit=960x600",
                    f"--title=NASA APOD: {title}",
                    "--force-window=yes",
                    "--loop-file=inf",
                    norm_url,
                ]
                subprocess.Popen(cmd, start_new_session=True)
                send_notification("Playing Video", f"NASA APOD: {title}")
                return {"success": True, "player": "mpv", "url": norm_url}
            except Exception as e:
                print(f"Error launching mpv: {e}", file=sys.stderr)

        # Fallback to browser
        return open_in_browser(prefer_video_url=True)

    else:
        # Image
        local_img = state.get("local_hd_image") or state.get("local_image")
        target = local_img if (local_img and os.path.exists(local_img)) else media_url
        if shutil.which("xdg-open"):
            subprocess.Popen(["xdg-open", target], start_new_session=True)
            return {"success": True, "player": "xdg-open", "target": target}
        return open_in_browser()


def view_image() -> dict:
    """Open full image in system image viewer (imv), binding Escape to quit, and restore panel on exit."""
    if not STATE_FILE.exists():
        fetch_apod()

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
    except Exception as e:
        return {"success": False, "error": str(e)}

    if not state.get("success"):
        return {"success": False, "error": "No APOD loaded"}

    if state.get("media_type") == "video":
        return play_media()

    # Prioritize already available local image for instant 0ms display
    image_path = state.get("local_hd_image") or state.get("local_image")
    if not image_path or not os.path.exists(image_path):
        image_path = download_hd_image(state) or state.get("local_image", "")

    if not image_path or not os.path.exists(image_path):
        return {"success": False, "error": "Image not found"}

    # Open with imv (with Escape key bound to quit)
    if shutil.which("imv"):
        try:
            env = os.environ.copy()
            cmd = ["imv", "-c", "bind <Escape> quit", str(image_path)]
            subprocess.run(cmd, env=env, check=False)

            # Reopen plugin panel after imv exits
            omarchy_bin = shutil.which("omarchy")
            if omarchy_bin:
                subprocess.Popen([omarchy_bin, "shell", "dorneles.nasa-apod", "open"], start_new_session=True)

            return {"success": True, "viewer": "imv", "path": str(image_path)}
        except Exception as e:
            print(f"Error launching imv: {e}", file=sys.stderr)

    elif shutil.which("xdg-open"):
        try:
            subprocess.run(["xdg-open", image_path], check=False)
            omarchy_bin = shutil.which("omarchy")
            if omarchy_bin:
                subprocess.Popen([omarchy_bin, "shell", "dorneles.nasa-apod", "open"], start_new_session=True)
            return {"success": True, "viewer": "xdg-open", "path": str(image_path)}
        except Exception as e:
            print(f"Error launching xdg-open: {e}", file=sys.stderr)

    return open_in_browser()


def open_in_browser(prefer_video_url: bool = False) -> dict:
    """Open current APOD in default browser."""
    if not STATE_FILE.exists():
        fetch_apod()

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
    except Exception as e:
        return {"success": False, "error": str(e)}

    if prefer_video_url and state.get("media_type") == "video":
        url = state.get("url") or state.get("web_url")
    else:
        url = state.get("web_url") or state.get("url")

    if not url:
        return {"success": False, "error": "No URL to open"}

    omarchy_bin = shutil.which("omarchy")
    if omarchy_bin:
        subprocess.Popen([omarchy_bin, "launch", "browser", url], start_new_session=True)
    elif shutil.which("xdg-open"):
        subprocess.Popen(["xdg-open", url], start_new_session=True)
    else:
        return {"success": False, "error": "No browser launcher available"}

    return {"success": True, "opened_url": url}


def main():
    parser = argparse.ArgumentParser(description="NASA APOD backend tool")
    subparsers = parser.add_subparsers(dest="action", help="Action to perform")

    # fetch
    fetch_parser = subparsers.add_parser("fetch", help="Fetch APOD data")
    fetch_parser.add_argument("--date", type=str, help="Date in YYYY-MM-DD format")
    fetch_parser.add_argument("--today", action="store_true", help="Fetch today's APOD")
    fetch_parser.add_argument("--random", action="store_true", help="Fetch random APOD date")
    fetch_parser.add_argument("--api-key", type=str, default=DEFAULT_API_KEY, help="NASA API Key")
    fetch_parser.add_argument("--force", action="store_true", help="Force refresh cache")

    # view (enlarged view in imv / default viewer)
    subparsers.add_parser("view", help="Open HD image in viewer (imv / default)")

    # play
    subparsers.add_parser("play", help="Play current APOD video or open media")

    # wallpaper
    subparsers.add_parser("wallpaper", help="Set current APOD as wallpaper")

    # save
    subparsers.add_parser("save", help="Save HD image to ~/Pictures/NASA_APOD/")

    # browser
    browser_parser = subparsers.add_parser("browser", help="Open APOD page in browser")
    browser_parser.add_argument("--video", action="store_true", help="Open direct video URL instead of archive page")

    # copy
    copy_parser = subparsers.add_parser("copy", help="Copy image or URL to clipboard")
    copy_parser.add_argument("--kind", choices=["image", "web", "media", "hd"], default="image")

    args = parser.parse_args()

    if args.action == "view":
        res = view_image()
        print(json.dumps(res, indent=2))
    elif args.action == "play":
        res = play_media()
        print(json.dumps(res, indent=2))
    elif args.action == "wallpaper":
        res = set_as_wallpaper()
        print(json.dumps(res, indent=2))
    elif args.action == "save":
        res = save_image_to_pictures()
        print(json.dumps(res, indent=2))
    elif args.action == "browser":
        prefer_video = getattr(args, "video", False)
        res = open_in_browser(prefer_video_url=prefer_video)
        print(json.dumps(res, indent=2))
    elif args.action == "copy":
        res = copy_to_clipboard(args.kind)
        print(json.dumps(res, indent=2))
    else:
        # Default: fetch
        target_date = None
        if hasattr(args, "random") and args.random:
            target_date = get_random_date()
        elif hasattr(args, "date") and args.date:
            target_date = args.date

        api_key = getattr(args, "api_key", DEFAULT_API_KEY)
        force = getattr(args, "force", False)

        state = fetch_apod(date_str=target_date, api_key=api_key, force_refresh=force)
        print(json.dumps(state, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
