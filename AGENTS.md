# AGENTS.md

## Project overview

**Gala** is a small, dependency-free Python web gallery server.

- Backend: `gala.py` (Python stdlib only)
- Frontend template + app logic: `gala.html` (inline CSS + vanilla JS)
- No package manager, no build step, no test suite

Primary workflow: run `gala.py`, browse media in the browser, navigate with keyboard, optionally move files to `deleted/`.

---

## Tech constraints

- Python **3.10+**
- Standard library only
- Keep implementation lightweight and simple
- Prefer small, surgical edits over large rewrites unless requested

---

## Repository map

- `gala.py` — CLI, HTTP server, media scanning, HTML generation, delete API
- `gala.html` — viewer UI + navigation + lazy loading + autoplay + delete UX
- `README.md` — user-facing docs
- `todo.txt` — informal notes
- `history.txt` — run history for non-default paths (gitignored)
- `.gitignore` — currently ignores `history.txt`

---

## Runtime / CLI

```bash
python gala.py [DIRECTORY] [--host HOST] [--port PORT] [--no-open]
```

Defaults:
- directory: `.`
- host: `127.0.0.1`
- port: `8000`
- browser opens automatically unless `--no-open`

---

## Backend behavior (`gala.py`)

### Media discovery

- Recursive scan via `Path.rglob("*")`
- Allowed extensions:
  - `IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif"}`
  - `VIDEO_EXTENSIONS = {".webm", ".mp4"}`
  - `ALLOWED_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS`
- Returns sorted relative POSIX paths
- Files under `<base_dir>/deleted/**` are excluded from listings

### Routes

- `GET /` (and `GET /?query`) → gallery HTML
- static files/media → served by `SimpleHTTPRequestHandler`
- `DELETE /api/delete?name=<relative-path>` → move file into `deleted/`

### Delete behavior

- Request path is URL-decoded and resolved under `base_dir`
- Path escapes are blocked with `relative_to(base_dir)`
- Move target: `<base_dir>/deleted/<relative-path>`
- Name collisions become `stem_1.ext`, `stem_2.ext`, ...

### Delete API status behavior

- `200` success: `{ "ok": true }`
- `400` missing filename
- `403` invalid file path or permission denied
- `404` file not found
- `500` unexpected error

### Other persistence

- Non-default launch paths are prepended to `history.txt` (best-effort read/write)

---

## Frontend behavior (`gala.html`)

### Viewer model

- One item per viewport (`100vh`) with vertical scroll snap
- Lazy load images/videos near current index
- Unload media outside keep window to reduce memory
- Uses `IntersectionObserver` to track visible/current item

### Media window strategy

Current implementation is diff-based (not full list scans each update):
- load radius: `LOAD_RADIUS = 2`
- keep radius: `KEEP_RADIUS = 5`
- tracks `keptStart` / `keptEnd`
- unloads only indices that leave previous keep window

### Video autoplay and audio

- Visible videos attempt autoplay
- If visible video is not loaded yet, it is loaded first, then autoplay is attempted
- Non-visible videos are paused and muted
- Audio toggle with `m`:
  - `unmutedMode = true` means only current/visible video can be unmuted
  - previous/non-current videos remain muted

> Note: browsers may still block unmuted autoplay based on autoplay policy.

### Keyboard shortcuts

- `j` → next item
- `k` → previous item
- `n` → random item from remaining pool (cycles before reset)
- `b` → back in navigation history
- `Space` → play/pause current video
- `m` → toggle audio mode (muted/unmuted mode)
- `x` → delete current item (calls `DELETE /api/delete`)
- `h` / `PageDown` → next path/group
- `l` / `PageUp` → previous path/group
- `u` / `Home` → first item in current path/group
- `i` / `End` → last item in current path/group

---

## Guidance for future agents

1. Read **both** `gala.py` and `gala.html` before making changes.
2. Keep dependency-free architecture.
3. Preserve keyboard-first workflow.
4. Preserve path safety in delete handling (`resolve()` + `relative_to(base_dir)`).
5. If changing shortcuts, API, or delete semantics, update `README.md` in same change.
6. Prefer simple logic over abstraction-heavy refactors.

---

## Manual verification checklist

After changes, verify:

1. `python gala.py` starts and serves `GET /`.
2. `GET /?x=1` still serves gallery.
3. Scroll loading/unloading works without major jank.
4. Visible videos autoplay; off-screen videos pause.
5. `m` toggles audio mode; only current video can be audible in unmuted mode.
6. `x` moves files into `deleted/` and removed file does not reappear on refresh.
7. Keyboard navigation (`j/k/n/b/h/l/u/i`, PgUp/PgDn/Home/End, Space) still works.
