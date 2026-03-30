# Code Review: gala.py & gala.html

Review focused on **simplicity**, **performance**, and **idiomatic Python** (prioritized in that order).

---

## Must Fix

### 1. ✅ Cache HTML template

`load_html_template()` reads `gala.html` from disk on every `GET /`. Cache it once at startup or on first use.

- **Category:** Performance
- **Files:** `gala.py` — `load_html_template()`, `generate_gallery_html()`

### 2. ✅ Prune excluded dirs during traversal

`list_media_files` uses `rglob("*")` and post-filters excluded directories (`deleted/`, `favorites/`). Switch to `os.walk()` with directory pruning so we never descend into those trees at all.

- **Category:** Performance + Simplicity
- **Files:** `gala.py` — `list_media_files()`

### 3. ✅ Replace `items.indexOf()` in observer with O(1) lookup

The `IntersectionObserver` callback calls `items.indexOf(entry.target)` on every visibility change — an O(n) scan per event. Use a `WeakMap` for constant-time index lookup. Update it when items are spliced in `deleteCurrent`.

- **Category:** Performance
- **Files:** `gala.html` — `handleIntersections()`, `deleteCurrent()`

### 4. ✅ Cache item metadata once in JS

`getMediaElements(item)` re-queries the DOM via `querySelector` on every call. `pathAt(i)` recomputes the path by parsing the filename string each time, including inside tight loops in `navigateToNextPath`/`navigateToPreviousPath`/`findPathStart`. Cache per-item metadata (media element refs, precomputed paths) once at startup and maintain it on deletion.

- **Category:** Performance
- **Files:** `gala.html` — `getMediaElements()`, `pathAt()`, navigation functions

### 5. ✅ Simplify `save_path_to_history`

Current logic uses `if path in existing_paths` then `existing_paths.remove(path)` — two linear scans, and it only removes one duplicate. Replace with a single filter pass that removes all occurrences:

```python
existing_paths = [p for p in existing_paths if p != path]
updated_paths = [path, *existing_paths]
```

- **Category:** Simplicity + Idiomatic Python
- **Files:** `gala.py` — `save_path_to_history()`

### 6. ✅ Remove dead code

- **Unreachable `raise RuntimeError`** in `_build_delete_destination`: the `for index in count(1):` loop is infinite, so the `raise` after it never executes. Rewrite with a simple `while` loop and drop the `itertools.count` import.
- **Unused `data-name` attribute**: `create_media_item_html` emits `data-name="{safe_name}"` but nothing in the HTML/JS reads it. Remove it and drop `import html` if no longer needed.
- **Category:** Simplicity
- **Files:** `gala.py` — `_build_delete_destination()`, `create_media_item_html()`

### 7. ✅ Validate `is_dir()` in `main()`, not just `exists()`

`main()` checks `if not base_directory.exists()` but should check `is_dir()` — passing a file path would produce confusing behavior rather than a clear error.

- **Category:** Correctness
- **Files:** `gala.py` — `main()`

---

## Should Fix

### 8. ✅ Simplify `_query_name_param`

```python
# current
return next(iter(query_params.get("name", [])), "")

# simpler
return query_params.get("name", [""])[0]
```

- **Category:** Simplicity
- **Files:** `gala.py` — `_query_name_param()`

### 9. ✅ Use `Path.cwd()` instead of `os.getcwd()`

`import os` is used solely for `os.getcwd()` in `GalleryHandler.__init__`. Replace with `Path.cwd()` and drop the `os` import.

- **Category:** Idiomatic Python
- **Files:** `gala.py` — `GalleryHandler.__init__()`, imports

### 10. ✅ Extract shared helpers for path-bound navigation

`navigateToFirstInPath` duplicates the backward-scan logic already in `findPathStart`. Reuse `findPathStart(currentIndex)` directly. For `navigateToLastInPath`, add a symmetric `findPathEnd` helper if needed.

- **Category:** Simplicity
- **Files:** `gala.html` — `navigateToFirstInPath()`, `navigateToLastInPath()`

---

## Nice to Have

### 11. Simplify path encoding/decoding flow

Python emits a URL-encoded filename, JS re-encodes it for API calls, and the server decodes it again. JS also re-parses the encoded filename for directory grouping. Consider separating the raw relative path (for actions/grouping) from the encoded URL (for `src`/`href`). Works correctly as-is, but adds unnecessary complexity.

- **Category:** Simplicity
- **Files:** `gala.py` — `create_media_item_html()`, `gala.html` — `getItemPath()`, API calls

### 12. Narrow broad `except Exception` / silent `pass`

Several places use `except Exception` or bare `except ... pass` blocks (e.g., `_delete_file`, `_favorite_file`, `webbrowser.open`). Acceptable for a small utility, but could mask unexpected errors.

- **Category:** Idiomatic Python
- **Files:** `gala.py` — `_delete_file()`, `_favorite_file()`, `main()`

### 13. Revisit `self.base_dir` vs `self.directory`

`GalleryHandler.__init__` stores `self.base_dir` as a `Path`, but `super().__init__()` already stores the same value as a string in `self.directory`. Maintaining both is slightly redundant. Keeping a `Path` on the handler is reasonable for ergonomics, but worth being aware of.

- **Category:** Simplicity
- **Files:** `gala.py` — `GalleryHandler.__init__()`

### 14. Reevaluate temp `Image()` preloading approach

`loadImage` creates a throwaway `new Image()` to preload, then sets `img.src` on success. This avoids showing a broken/half-loaded state on the real element, but creates an extra object and decode pass. Setting `onload`/`onerror` directly on the real `<img>` element is simpler and avoids the overhead. Lower priority unless profiling shows it matters.

- **Category:** Performance
- **Files:** `gala.html` — `loadImage()`
