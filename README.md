# Gala

A simple, dependency-free Python server that creates a fullscreen web gallery for images and videos in any folder (recursively).

## Features

- **Recursive gallery** for supported media under the selected directory
- **Fullscreen viewer** with vertical scroll-snap (one item per screen)
- **Lazy loading + unloading** for better memory/performance on large galleries
- **Autoplay video in view** and pause when out of view
- **Keyboard-first navigation** (next/prev, random, back, path navigation)
- **Audio mode toggle** with `m` (unmuted mode keeps only the current/visible video audible)
- **Favorites flow**: copy current media file into a local `favorites/` folder (original kept untouched)
- **Safe delete flow**: moving files into a local `deleted/` folder (not immediate permanent removal)

## Requirements

- **Python 3.10+**
- Standard library only (no external dependencies)

## Usage

```bash
python gala.py [DIRECTORY] [--host HOST] [--port PORT] [--no-open]
```

- `DIRECTORY`: folder to serve (default: `.`)
- `--host`: bind host (default: `127.0.0.1`)
- `--port`: bind port (default: `8000`)
- `--no-open`: do not auto-open browser on start

### Examples

```bash
# Serve current folder and open browser
python gala.py

# Serve a specific folder
python gala.py "D:\Photos"      # Windows
python gala.py ~/Pictures         # macOS/Linux

# Serve on all interfaces without opening browser
python gala.py . --host 0.0.0.0 --port 8080 --no-open
```

When started, Gala prints:

```text
Serving /absolute/path/to/DIRECTORY at http://127.0.0.1:8000/
```

Stop with `Ctrl+C`.

---

## Supported media types

Defined in `gala.py`:

- Images: `.jpg`, `.jpeg`, `.png`, `.gif`
- Videos: `.webm`, `.mp4`

You can customize these via:

- `IMAGE_EXTENSIONS`
- `VIDEO_EXTENSIONS`
- `ALLOWED_EXTENSIONS`

---

## Keyboard shortcuts (browser)

### Item navigation

- `j` → next item
- `k` → previous item
- `n` → random unviewed item (cycles through all before resetting)
- `b` → back to previous visited item

### Path/group navigation

- `h` or `PageDown` → next path/group
- `l` or `PageUp` → previous path/group
- `u` or `Home` → first item in current path/group
- `i` or `End` → last item in current path/group

### Playback, favorites, and delete

- `Space` → play/pause current video
- `m` → toggle audio mode for the current video (unmuted/muted)
- `f` → copy current media file to `favorites/` (overwrites existing favorite copy)
- `x` → move current file to `deleted/`

Notes:

- Clicking an image opens it in a new tab.
- In unmuted mode, only the current/visible video has sound; other videos remain muted.
- Browsers may still block unmuted autoplay depending on autoplay policy.
- Files under `deleted/` and `favorites/` are excluded from gallery listing.

---

## API

Available while the server is running (paths are relative to served directory):

- `GET /` → gallery HTML page
- `POST /api/favorite?name=RELATIVE_PATH` → copy supported media to `favorites/` (overwrite if present)
- `DELETE /api/delete?name=RELATIVE_PATH` → move file to `deleted/`

### Examples

```bash
# Favorite (copy) supported media
curl -X POST "http://127.0.0.1:8000/api/favorite?name=subdir%2Fphoto.jpg"

# Delete (move) a media file
curl -X DELETE "http://127.0.0.1:8000/api/delete?name=subdir%2Fphoto.jpg"
```

Success response:

```json
{ "ok": true }
```

Favorite responses also include an overwrite hint:

```json
{ "ok": true, "overwritten": false }
```

Error response shape:

```json
{ "ok": false, "error": "..." }
```

Common statuses:

- `400` missing filename / invalid media target (e.g., non-media)
- `403` invalid path or permission denied
- `404` file not found

---

## Favorites behavior

Favorites are implemented as a direct file copy (no transcoding/re-encoding):

- Source: `<base_dir>/<relative_path>`
- Destination: `<base_dir>/favorites/<relative_path>`

If destination already exists, it is overwritten.

---

## Delete behavior

Deletes are implemented as a move operation for supported media files (outside `deleted/` and `favorites/`):

- Source: `<base_dir>/<relative_path>`
- Destination: `<base_dir>/deleted/<relative_path>`

If destination exists, a suffix is added:

- `name.jpg` → `name_1.jpg`, `name_2.jpg`, etc.

---

## Safety and security

- **No authentication**: anyone with access to the server can favorite (copy) and delete (move) files.
- **Default is local-only** (`127.0.0.1`), which is safer.
- If using `0.0.0.0`, only do so on trusted networks.

---

## Development notes

- Backend logic: `gala.py`
- Frontend template and client behavior: `gala.html`
- Last-used non-default directories are stored in `history.txt` (best-effort)
