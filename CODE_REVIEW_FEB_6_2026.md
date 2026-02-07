# Code Review — February 6, 2026

Scope reviewed:

- `gala.py`
- `gala.html`

Review criteria:

- Simplicity (less code, same features)
- Performance
- Readability
- Bugs / correctness

Sorted by relevance (highest first).

---

## 1) High relevance (bugs / correctness)

1. **Deleted files can reappear after refresh**
    - `list_media_files()` recursively scans everything under `base_dir`, including `base_dir/deleted/`.
    - Since delete currently _moves_ files there, they can show up again on reload.
    - **Impact:** delete UX appears broken.
    - **Recommendation:** exclude `deleted/` subtree from scan.

2. **Invalid delete path can return 500 (should be 4xx)**
    - In `_delete_file()`, `relative_to(self.base_dir)` raises `ValueError` for outside paths.
    - This currently falls into generic `except Exception` → 500 + internal error text.
    - **Impact:** incorrect status code and potential information leak.
    - **Recommendation:** catch `ValueError` and return `403` (or `400`) with a generic message.

3. **`scrollIntoView({ behavior: "instant" })` is non-standard**
    - Standard behavior values are `"auto"` or `"smooth"`.
    - Can throw in some browsers and break post-delete flow.
    - **Impact:** fragile behavior after deletion.
    - **Recommendation:** replace `"instant"` with `"auto"`.

4. **`GET /?query` won’t serve gallery root**
    - `do_GET()` checks `self.path == "/"` exactly.
    - Root with query string is routed as static and may 404.
    - **Recommendation:** parse URL and compare `parsed.path == "/"`.

---

## 2) Medium relevance (performance)

5. **Unload strategy is O(n) on each visibility update**
    - `unloadMediaOutOfRange()` loops through all items whenever center changes.
    - For large galleries, this may cause scroll jank.
    - **Recommendation:** track previous keep-range and update only diffs.

6. **Rendering all items in DOM scales poorly at very large counts**
    - Thousands of `.item` nodes and observers create overhead.
    - Lazy media loading helps bandwidth but not DOM size cost.
    - **Recommendation:** if needed, implement windowing/virtualization.

7. **Full recursive scan on each page load**
    - `GET /` runs `rglob` each time.
    - Can be slow for large/network directories.
    - **Recommendation:** optional caching with invalidation on delete/manual refresh.

---

## 3) Lower relevance (simplicity / readability)

8. **`viewedItems` state appears unnecessary**
    - It is maintained and adjusted, but random behavior is effectively driven by `remainingItems`.
    - **Recommendation:** remove `viewedItems` to reduce complexity.

9. **Path navigation code has duplication**
    - `navigateToNextPath`, `navigateToPreviousPath`, `navigateToFirstInPath`, and `navigateToLastInPath` duplicate traversal logic.
    - **Recommendation:** extract shared helper(s) to reduce code size and maintenance load.

10. **Key mapping readability/expectation mismatch**

- `h` = next path and `l` = previous path may surprise users.
- **Recommendation:** either swap mappings or add explicit in-code/docs note.

11. **Documentation drift**

- `README.md` does not fully match implementation (API + delete behavior + key list).
- **Recommendation:** update README with current behavior to reduce confusion.

---

## Quick health check

- `python -m py_compile gala.py` passes.
