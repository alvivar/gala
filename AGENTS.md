# AGENTS.md

## Project overview

**Gala** is a small, dependency-free Python web app that serves a fullscreen, scroll-snap media gallery for a directory tree.

- Backend: `gala.py` (Python stdlib only)
- Frontend template: `gala.html` (inline CSS + vanilla JS)
- No build step, no package manager, no tests currently

Primary workflow: run `gala.py`, browse media, navigate with keyboard, optionally delete items.

---

## Tech stack and constraints

- Python **3.10+**
- Standard library only (`http.server`, `pathlib`, `argparse`, etc.)
- No external JS/CSS dependencies
- Intended to stay lightweight and simple

If adding features, prefer stdlib + plain JS and avoid introducing frameworks/toolchains unless explicitly requested.

---

## Repository map

- `gala.py` — server, media discovery, HTML generation, delete API, CLI
- `gala.html` — gallery template and all client-side behavior
- `README.md` — user docs (note: currently partially out of sync with implementation)
- `todo.txt` — informal backlog
- `history.txt` — local run history (ignored in git)
- `.gitignore` — currently ignores `history.txt`

---

## How to run

```bash
python gala.py [DIRECTORY] [--host HOST] [--port PORT] [--no-open]
```

Defaults:

- `DIRECTORY=.`
- `--host 127.0.0.1`
- `--port 8000`
- Browser auto-opens unless `--no-open`

Stop with `Ctrl+C`.

---

## Backend behavior (`gala.py`)

### Media scanning

- Uses recursive `Path.rglob("*")`
- Allowed extensions are controlled by:
    - `IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif"}`
    - `VIDEO_EXTENSIONS = {".webm", ".mp4"}`
- Combined as `ALLOWED_EXTENSIONS`
- Returns sorted relative POSIX-style paths

### Routes

- `GET /` → rendered gallery HTML (`gala.html` + `{items_html}` substitution)
- Static files/media served by `SimpleHTTPRequestHandler`
- `DELETE /api/delete?name=<relative-path>` → moves a file into `deleted/` under served base dir

### Delete semantics

- File path is URL-decoded, resolved, and validated via `relative_to(base_dir)`
- Instead of permanent deletion, file is moved to:
    - `<base_dir>/deleted/<original-relative-path>`
- Name collisions in `deleted/` are resolved as `stem_1.ext`, `stem_2.ext`, etc.

### Persistence

- When run with a non-default directory arg (`args.directory != "."`), absolute path is prepended to `history.txt`
- `history.txt` is best-effort; read/write failures are ignored

---

## Frontend behavior (`gala.html`)

### Rendering and loading

- One `.item` per viewport (`100vh`), vertical scroll-snap
- Lazy-loading for images/videos around current index
- Media outside a range is unloaded to reduce memory
- `IntersectionObserver` updates current item and auto-plays visible loaded video

### Keyboard controls (as implemented)

- `j` → next item
- `k` → previous item
- `n` → random unviewed item (cycles through all)
- `b` → back in navigation history
- `Space` → toggle play/pause on current video
- `x` → delete current item (calls `DELETE /api/delete`)
- `h` / `PageDown` → next path/group
- `l` / `PageUp` → previous path/group
- `u` / `Home` → first item in current path/group
- `i` / `End` → last item in current path/group

---

## Important doc/code mismatches

`README.md` appears stale relative to current code:

- README mentions `GET /api/list` and `POST /api/delete` but code currently implements only `DELETE /api/delete`.
- README says delete removes from disk immediately; current code moves files to a `deleted/` folder.
- README shortcut list omits newer path-navigation keys (`h/l/u/i`, PgUp/PgDn/Home/End).

If you change behavior, update both code and README to keep them aligned.

---

## Known quirks / gotchas

- Because media scan is recursive from base dir, files moved into `deleted/` still match extension filters and can reappear on refresh.
- Template injection relies on exact `{items_html}` token in `gala.html`.
- Paths in DOM use URL-encoded POSIX style; delete API expects that encoded `data-filename` value.

---

## Guidance for future AI/code agents

1. **Read both `gala.py` and `gala.html` before changes** (logic is split across backend/frontend).
2. Keep implementation minimal and dependency-free unless user asks otherwise.
3. Preserve keyboard-first workflow and performance (lazy loading, unload strategy).
4. Be careful with path/security logic in delete handling (`resolve()` + `relative_to(base_dir)`).
5. When adding/changing shortcuts or API endpoints, update docs (`README.md`) in the same change.
6. Prefer small, surgical edits; this project is intentionally compact.

---

## Manual verification checklist

After modifications, manually verify:

1. Server starts and serves `GET /`.
2. Images and videos load while scrolling.
3. Video autoplay/pause behavior works when entering/leaving viewport.
4. Keyboard shortcuts still work (item nav, random, back, path nav, play/pause).
5. Delete action succeeds and UI updates correctly.
6. Reload behavior is acceptable (especially around `deleted/` handling).
