# Gala

A simple, dependency-free Python server that creates a fullscreen web gallery for images and videos in any folder (recursively).

## Features

- **Recursive gallery** for supported media under the selected directory
- **Fullscreen viewer** with vertical scroll-snap (one item per screen)
- **Lazy loading + unloading** for better memory/performance on large galleries
- **Autoplay video in view** and pause when out of view
- **Keyboard-first navigation** (next/prev, random, back, path navigation)
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

### Playback and delete

- `Space` → play/pause current video
- `x` → move current file to `deleted/`

Notes:

- Clicking an image opens it in a new tab.
- Files moved to `deleted/` are excluded from gallery listing.

---

## API

Available while the server is running (paths are relative to served directory):

- `GET /` → gallery HTML page
- `DELETE /api/delete?name=RELATIVE_PATH` → move file to `deleted/`

### Example

```bash
curl -X DELETE "http://127.0.0.1:8000/api/delete?name=subdir%2Fphoto.jpg"
```

Success response:

```json
{ "ok": true }
```

Error response shape:

```json
{ "ok": false, "error": "..." }
```

Common statuses:

- `400` missing filename
- `403` invalid path or permission denied
- `404` file not found

---

## Delete behavior

Deletes are implemented as a move operation:

- Source: `<base_dir>/<relative_path>`
- Destination: `<base_dir>/deleted/<relative_path>`

If destination exists, a suffix is added:

- `name.jpg` → `name_1.jpg`, `name_2.jpg`, etc.

---

## Safety and security

- **No authentication**: anyone with access to the server can delete (move) files.
- **Default is local-only** (`127.0.0.1`), which is safer.
- If using `0.0.0.0`, only do so on trusted networks.

---

## Development notes

- Backend logic: `gala.py`
- Frontend template and client behavior: `gala.html`
- Last-used non-default directories are stored in `history.txt` (best-effort)
