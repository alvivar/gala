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


def load_html_template() -> str:
    """Load HTML template from external file."""
    template_path = Path(__file__).parent / "gala.html"
    return template_path.read_text(encoding="utf-8")


def generate_gallery_html(base_dir: Path, files: list[str]) -> bytes:
    if files:
        items_html = "\n".join(create_media_item_html(filename) for filename in files)
    else:
        items_html = '<p style="padding:2rem;color:#aaa">No media files found.</p>'

    html_template = load_html_template()
    html_document = html_template.replace("{items_html}", items_html)

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
        else:
            super().do_GET()

    def do_DELETE(self) -> None:
        if not self._is_delete_endpoint():
            self.send_error(404, "Not Found")
            return

        query_params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        filename = (query_params.get("name") or [""])[0]
        self._handle_delete_request(filename)

    def _serve_gallery(self) -> None:
        files = list_media_files(self.base_dir)
        content = generate_gallery_html(self.base_dir, files)
        self._send_response(200, "text/html; charset=utf-8", content)

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

    def _is_delete_endpoint(self) -> bool:
        return urllib.parse.urlparse(self.path).path == "/api/delete"

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
        description="a simple python server that recursively creates a web gallery for images and videos in any folder"
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="directory to serve (default: current working directory)",
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
