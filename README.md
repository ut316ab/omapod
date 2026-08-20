#  omapod - NASA Astronomy Picture of the Day for Omarchy

**omapod** is an interactive **NASA APOD (Astronomy Picture of the Day)** status bar plugin for **Omarchy Linux (Hyprland / Quickshell)**.

---

## ✨ Features

-  **Classic Rocket Icon in Status Bar:** Clean, unmistakable Nerd Font rocket (``) icon on the top status bar.
- 🌌 **Astronomy Popup Panel:**
  - High-definition astronomy photos.
  - **Inline & External Video Player:** Direct MP4 videos play seamlessly inside the card with seek bar, time display, play/pause and volume controls; YouTube/Vimeo streams launch directly in MPV player.
  - Formatted title, date (displayed right under the title), and scientific explanations.
- 🧭 **Time Navigation:**
  - **Previous (◀):** Navigate back through decades of NASA astronomy history.
  - **Today (📅):** Return instantly to today's featured media.
  - **Next (▶):** Advance forward (automatically disabled on today).
  - **Random (🔀):** Discover fascinating random astronomy photos since June 16, 1995.
- 🖼️ **1-Click Wallpaper:** Set any APOD image as your Omarchy desktop background (strictly on-demand via the Wallpaper button).
- 💾 **Save to Pictures:** Export HD images directly to `~/Pictures/NASA_APOD/`.
- 📋 **Copy Image to Clipboard:** Direct binary image copying via `wl-copy` to paste directly into Discord, Telegram, GIMP, Slack, etc. (disabled for videos).
- 🌐 **Robust Dual Backend:** NASA API with automatic zero-rate-limit fallback to the official NASA APOD HTML archive.
- ⚡ **Smart Cache:** Caches metadata and media in `~/.cache/omarchy-omapod/`.

---

## ⌨️ Keyboard Shortcuts (Inside Panel)

| Key | Action |
|---|---|
| <kbd>Space</kbd> or <kbd>P</kbd> | Play / Pause video |
| <kbd>M</kbd> | Mute / Unmute video audio |
| <kbd>V</kbd> | Open video in external MPV Player |
| <kbd>Esc</kbd> | Close popup panel |
| <kbd>←</kbd> (Left Arrow) | Previous day |
| <kbd>→</kbd> (Right Arrow) | Next day (disabled on Today) |
| <kbd>T</kbd> | Today's picture |
| <kbd>R</kbd> | Random astronomy picture |
| <kbd>W</kbd> | Set as wallpaper |
| <kbd>S</kbd> | Save image to `~/Pictures/NASA_APOD/` |
| <kbd>C</kbd> | Copy image to clipboard |
| <kbd>B</kbd> | Open NASA webpage in browser |

---

## 🖱️ Mouse Actions on the Status Bar Icon

- **Left-Click / Right-Click:** Toggle the omapod panel.
- **Middle-Click (Scroll):** Fetch and display a random astronomy picture.

---

## ⚙️ CLI / IPC Controls

```bash
# Toggle / Open / Close
omarchy-shell dorneles.omapod toggle
omarchy-shell dorneles.omapod open
omarchy-shell dorneles.omapod close

# Play video
omarchy-shell dorneles.omapod play

# Navigation
omarchy-shell dorneles.omapod refresh
omarchy-shell dorneles.omapod random

# Actions
omarchy-shell dorneles.omapod wallpaper
omarchy-shell dorneles.omapod save
omarchy-shell dorneles.omapod copy
omarchy-shell dorneles.omapod browser
```
