import argparse
import html
import json
import os
import sys
import urllib.parse
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif"}
VIDEO_EXTENSIONS = {".webm", ".mp4"}
ALLOWED_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS


def list_media_files(base_dir: Path) -> list[str]:
    try:
        files = [
            entry.relative_to(base_dir).as_posix()
            for entry in base_dir.rglob("*")
            if entry.is_file() and entry.suffix.lower() in ALLOWED_EXTENSIONS
        ]
        return sorted(files)
    except FileNotFoundError:
        return []


def create_media_item_html(filename: str) -> str:
    safe_name = html.escape(filename, quote=True)
    quoted_src = urllib.parse.quote(filename, safe="/")
    extension = Path(filename).suffix.lower()

    if extension in VIDEO_EXTENSIONS:
        media_tag = f'<video src="{quoted_src}" controls muted playsinline></video>'
    else:
        media_tag = f'<a href="{quoted_src}" target="_blank" rel="noopener"><img src="{quoted_src}" alt="{safe_name}" /></a>'

    return f'<div class="item" data-name="{safe_name}" data-filename="{quoted_src}">{media_tag}</div>'


def generate_gallery_html(base_dir: Path, files: list[str]) -> bytes:
    if files:
        items_html = "\n".join(create_media_item_html(filename) for filename in files)
    else:
        items_html = '<p style="padding:2rem;color:#aaa">No media files found.</p>'

    html_document = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>Gala</title>
    <style>
        * {{
            box-sizing: border-box;
        }}
        html, body {{
            height: 100%;
        }}
        body {{
            margin: 0;
            font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
            background: #111;
            color: #eee;
        }}
        .grid {{
            display: block;
            height: 100vh;
            overflow-y: auto;
            scroll-snap-type: y mandatory;
            scroll-behavior: smooth;
            padding: 0;
            margin: 0;
        }}
        .item {{
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #000;
            border: 0;
            border-radius: 0;
            overflow: hidden;
            scroll-snap-align: start;
            scroll-snap-stop: always;
        }}
        .item img, .item video {{
            display: block;
            max-width: 100vw;
            max-height: 100vh;
            width: auto;
            height: auto;
            object-fit: contain;
            background: #000;
        }}
        .item a {{
            display: flex;
            width: 100%;
            height: 100%;
            align-items: center;
            justify-content: center;
            color: inherit;
            text-decoration: none;
        }}
    </style>
</head>
<body>
    <div class="grid">{items_html}</div>
    <script>
        (function() {{
            // State management
            let items = Array.from(document.querySelectorAll('.item'));
            let current = items[0] || null;
            let currentIndex = 0;
            let history = [];

            // Random navigation state
            let remainingItems = [...Array(items.length).keys()];
            let viewedItems = new Set();

            // Initialize intersection observer for tracking current item
            const observer = new IntersectionObserver(entries => {{
                entries.forEach(entry => {{
                    const video = entry.target.querySelector('video');

                    if (entry.isIntersecting && entry.intersectionRatio >= 0.6) {{
                        // Update current item tracking
                        current = entry.target;
                        currentIndex = items.indexOf(entry.target);
                        console.log('Current image:', current.getAttribute('data-filename'));

                        // Auto-play videos when they enter view
                        if (video) {{
                            video.play();
                        }}
                    }} else {{
                        // Auto-pause and mute videos when out of sight
                        if (video && !video.paused) {{
                            video.pause();
                            video.muted = true;
                        }}
                    }}
                }});
            }}, {{ threshold: [0, 0.6, 1] }});

            // Start observing all items
            items.forEach(item => observer.observe(item));

            // Utility Functions
            function findClosestToCenter() {{
                const center = innerHeight / 2;
                let closest = null;
                let minDistance = Infinity;

                items.forEach(item => {{
                    const rect = item.getBoundingClientRect();
                    const itemCenter = rect.top + rect.height / 2;
                    const distance = Math.abs(itemCenter - center);

                    if (distance < minDistance) {{
                        minDistance = distance;
                        closest = item;
                    }}
                }});

                return closest;
            }}

            function navigateToIndex(targetIndex, addToHistory = true) {{
                if (addToHistory && currentIndex !== targetIndex) {{
                    history.push(currentIndex);
                }}

                items[targetIndex].scrollIntoView({{
                    behavior: 'smooth',
                    block: 'start'
                }});
            }}

            // Video Controls
            function toggleCurrentVideo() {{
                if (!current) return;

                const video = current.querySelector('video');
                if (!video) return;

                if (video.paused) {{
                    video.play();
                }} else {{
                    video.pause();
                }}
            }}

            // Navigation Functions
            function navigateToNext() {{
                if (items.length === 0) return;

                const nextIndex = (currentIndex + 1) % items.length;
                navigateToIndex(nextIndex);
            }}

            function navigateToPrevious() {{
                if (items.length === 0) return;

                const prevIndex = (currentIndex - 1 + items.length) % items.length;
                navigateToIndex(prevIndex);
            }}

            function navigateToRandom() {{
                if (items.length === 0) return;

                // Reset cycle if all items have been viewed
                if (remainingItems.length === 0) {{
                    remainingItems = [...Array(items.length).keys()];
                    viewedItems.clear();
                    console.log('All items viewed, restarting cycle');
                }}

                // Mark current item as viewed
                const currentInRemaining = remainingItems.indexOf(currentIndex);
                if (currentInRemaining !== -1) {{
                    remainingItems.splice(currentInRemaining, 1);
                    viewedItems.add(currentIndex);
                }}

                // Navigate to random unviewed item
                if (remainingItems.length > 0) {{
                    const randomIndex = Math.floor(Math.random() * remainingItems.length);
                    const targetIndex = remainingItems[randomIndex];

                    navigateToIndex(targetIndex);
                    console.log(`Navigating to random item ${{targetIndex + 1}} of ${{items.length}}`);
                }}
            }}

            function navigateBackward() {{
                if (history.length === 0) return;

                const previousIndex = history.pop();
                navigateToIndex(previousIndex, false);
            }}

            // Deletion Functionality
            async function deleteCurrent() {{
                if (!current) return;

                const filename = current.getAttribute('data-filename');
                if (!filename) return;

                console.log('Deleting:', filename);

                try {{
                    // Send delete request
                    const response = await fetch('/api/delete?name=' + encodeURIComponent(filename), {{
                        method: 'DELETE'
                    }});

                    const data = await response.json().catch(() => ({{}}));

                    if (!response.ok || !data.ok) {{
                        const errorMessage = data.error ? ': ' + data.error : '';
                        alert('Delete failed' + errorMessage);
                        return;
                    }}

                    // Clean up video resources
                    const video = current.querySelector('video');
                    if (video) {{
                        try {{
                            video.pause();
                            video.src = '';
                        }} catch (e) {{}}
                    }}

                    // Remove from DOM and tracking
                    observer.unobserve(current);
                    current.remove();

                    const removedIndex = items.indexOf(current);
                    if (removedIndex !== -1) {{
                        items.splice(removedIndex, 1);

                        // Update random navigation state
                        remainingItems = remainingItems
                            .map(idx => idx > removedIndex ? idx - 1 : idx)
                            .filter(idx => idx !== removedIndex);

                        // Update viewed items set
                        const newViewedItems = new Set();
                        viewedItems.forEach(idx => {{
                            if (idx !== removedIndex) {{
                                const adjustedIndex = idx > removedIndex ? idx - 1 : idx;
                                newViewedItems.add(adjustedIndex);
                            }}
                        }});
                        viewedItems = newViewedItems;

                        // Update history indices
                        history = history
                            .map(idx => idx > removedIndex ? idx - 1 : idx)
                            .filter(idx => idx !== removedIndex);
                    }}

                    // Navigate to next item or show empty state
                    if (items.length > 0) {{
                        const target = findClosestToCenter();
                        if (target) {{
                            target.scrollIntoView({{
                                behavior: 'instant',
                                block: 'start'
                            }});

                            current = target;
                            currentIndex = items.indexOf(target);
                            console.log('Current image:', current.getAttribute('data-filename'));
                        }}
                    }} else {{
                        document.body.innerHTML = '<p style="padding:2rem;color:#aaa">No media files remain.</p>';
                    }}
                }} catch (error) {{
                    alert('Delete failed: ' + error);
                }}
            }}

            // Keyboard Controls
            document.addEventListener('keydown', e => {{
                const key = e.key.toLowerCase();

                switch (key) {{
                    case 'x':
                        e.preventDefault();
                        deleteCurrent();
                        break;
                    case 'j':
                        e.preventDefault();
                        navigateToNext();
                        break;
                    case 'k':
                        e.preventDefault();
                        navigateToPrevious();
                        break;
                    case 'n':
                        e.preventDefault();
                        navigateToRandom();
                        break;
                    case 'b':
                        e.preventDefault();
                        navigateBackward();
                        break;
                    case ' ':
                        e.preventDefault();
                        toggleCurrentVideo();
                        break;
                }}
            }});
        }})();
    </script>
</body>
</html>"""

    return html_document.encode("utf-8")


class GalleryHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, directory: str | None = None, **kwargs):
        base = Path(directory or os.getcwd()).resolve()
        self.base_dir: Path = base
        super().__init__(*args, directory=str(base), **kwargs)

    def do_GET(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path == "/":
            self._serve_gallery()
        elif path == "/api/list":
            self._serve_file_list()
        else:
            super().do_GET()

    def do_DELETE(self) -> None:
        if not self._is_delete_endpoint():
            self.send_error(404, "Not Found")
            return

        query_params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        filename = (query_params.get("name") or [""])[0]
        self._handle_delete_request(filename)

    def do_POST(self) -> None:
        if not self._is_delete_endpoint():
            self.send_error(404, "Not Found")
            return

        content_length = int(self.headers.get("Content-Length") or 0)
        if content_length == 0:
            self._handle_delete_request("")
            return

        raw_data = self.rfile.read(content_length)
        filename = self._extract_filename_from_post_data(raw_data)
        self._handle_delete_request(filename)

    def _is_delete_endpoint(self) -> bool:
        return urllib.parse.urlparse(self.path).path == "/api/delete"

    def _serve_gallery(self) -> None:
        files = list_media_files(self.base_dir)
        content = generate_gallery_html(self.base_dir, files)
        self._send_response(200, "text/html; charset=utf-8", content)

    def _serve_file_list(self) -> None:
        files = list_media_files(self.base_dir)
        content = json.dumps({"files": files}).encode("utf-8")
        self._send_response(200, "application/json; charset=utf-8", content)

    def _extract_filename_from_post_data(self, raw_data: bytes) -> str:
        if not raw_data:
            return ""

        try:
            return json.loads(raw_data.decode("utf-8")).get("name", "")
        except (json.JSONDecodeError, UnicodeDecodeError):
            try:
                query_string = urllib.parse.parse_qs(raw_data.decode("utf-8"))
                return (query_string.get("name") or [""])[0]
            except UnicodeDecodeError:
                return ""

    def _handle_delete_request(self, filename: str) -> None:
        if not filename:
            self._send_json_response(400, {"ok": False, "error": "Missing filename"})
            return

        decoded_filename = urllib.parse.unquote(filename)
        file_path = (self.base_dir / decoded_filename).resolve()

        try:
            file_path.unlink()
            self._send_json_response(200, {"ok": True})
        except FileNotFoundError:
            self._send_json_response(404, {"ok": False, "error": "File not found"})
        except PermissionError:
            self._send_json_response(403, {"ok": False, "error": "Permission denied"})
        except Exception as error:
            self._send_json_response(500, {"ok": False, "error": str(error)})

    def _send_response(
        self, status_code: int, content_type: str, content: bytes
    ) -> None:
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_json_response(self, status_code: int, data: dict) -> None:
        content = json.dumps(data).encode("utf-8")
        self._send_response(status_code, "application/json; charset=utf-8", content)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Serve a dynamic gallery and allow deletion with 'x'."
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="Directory to serve (default: current working directory)",
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Port to bind (default: 8000)"
    )
    parser.add_argument(
        "--no-open", action="store_true", help="Do not open browser on start"
    )
    args = parser.parse_args()

    base_directory = Path(args.directory).resolve()
    if not base_directory.exists():
        print(f"Directory not found: {base_directory}", file=sys.stderr)
        sys.exit(1)

    RequestHandler = partial(GalleryHandler, directory=str(base_directory))
    server = ThreadingHTTPServer((args.host, args.port), RequestHandler)

    server_url = f"http://{args.host}:{args.port}/"
    print(f"Serving {base_directory} at {server_url}")

    if not args.no_open:
        try:
            webbrowser.open(server_url)
        except Exception:
            pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
