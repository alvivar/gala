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
        media_tag = f'<video data-src="{quoted_src}" controls muted playsinline class="lazy-video" preload="none"></video>'
    else:
        media_tag = f'<a href="{quoted_src}" target="_blank" rel="noopener"><img data-src="{quoted_src}" alt="{safe_name}" class="lazy-image" /></a>'

    return f'<div class="item" data-name="{safe_name}" data-filename="{quoted_src}">{media_tag}</div>'


def load_html_template() -> str:
    template_path = Path(__file__).parent / "gala.html"
    return template_path.read_text(encoding="utf-8")


def generate_gallery_html(files: list[str]) -> bytes:
    if files:
        items_html = "\n".join(create_media_item_html(filename) for filename in files)
    else:
        items_html = '<p style="padding:2rem;color:#aaa">No media files found.</p>'

    html_template = load_html_template()
    html_document = html_template.replace("{items_html}", items_html)
    return html_document.encode("utf-8")


def save_path_to_history(path: str) -> None:
    history_file = Path("history.txt")

    existing_paths = []
    if history_file.exists():
        try:
            content = history_file.read_text(encoding="utf-8").strip()
            if content:
                existing_paths = [p for p in content.split("\n") if p.strip()]
        except Exception:
            pass

    try:
        existing_paths.remove(path)
    except ValueError:
        pass

    updated_paths = [path] + existing_paths
    try:
        history_file.write_text("\n".join(updated_paths) + "\n", encoding="utf-8")
    except Exception:
        pass


class GalleryHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, directory: str | None = None, **kwargs):
        self.base_dir = Path(directory or os.getcwd()).resolve()
        super().__init__(*args, directory=str(self.base_dir), **kwargs)

    def do_GET(self) -> None:
        if self.path == "/":
            self._serve_gallery()
        else:
            super().do_GET()

    def do_DELETE(self) -> None:
        if urllib.parse.urlparse(self.path).path != "/api/delete":
            self.send_error(404, "Not Found")
            return

        query_params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        filename = (query_params.get("name") or [""])[0]
        self._delete_file(filename)

    def _serve_gallery(self) -> None:
        files = list_media_files(self.base_dir)
        content = generate_gallery_html(files)
        self._send_response(200, "text/html; charset=utf-8", content)

    def _delete_file(self, filename: str) -> None:
        if not filename:
            self._send_json(400, {"ok": False, "error": "Missing filename"})
            return

        file_path = (self.base_dir / urllib.parse.unquote(filename)).resolve()

        try:
            file_path.unlink()
            self._send_json(200, {"ok": True})
        except FileNotFoundError:
            self._send_json(404, {"ok": False, "error": "File not found"})
        except PermissionError:
            self._send_json(403, {"ok": False, "error": "Permission denied"})
        except Exception as error:
            self._send_json(500, {"ok": False, "error": str(error)})

    def _send_response(self, status: int, content_type: str, content: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_json(self, status: int, data: dict) -> None:
        content = json.dumps(data).encode("utf-8")
        self._send_response(status, "application/json; charset=utf-8", content)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Simple web gallery server for images and videos"
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="directory to serve (default: current directory)",
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="host to bind (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="port to bind (default: 8000)"
    )
    parser.add_argument(
        "--no-open", action="store_true", help="do not open browser on start"
    )
    args = parser.parse_args()

    base_directory = Path(args.directory).resolve()
    if not base_directory.exists():
        print(f"Directory not found: {base_directory}", file=sys.stderr)
        sys.exit(1)

    if args.directory != ".":
        save_path_to_history(str(base_directory))

    handler = partial(GalleryHandler, directory=str(base_directory))
    server = ThreadingHTTPServer((args.host, args.port), handler)
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
