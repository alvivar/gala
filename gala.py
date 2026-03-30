import argparse
import json
import os
import shutil
import sys
import urllib.parse
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif"}
VIDEO_EXTENSIONS = {".webm", ".mp4"}
ALLOWED_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS
DELETED_DIR_NAME = "deleted"
FAVORITES_DIR_NAME = "favorites"
EXCLUDED_MEDIA_DIR_NAMES = {DELETED_DIR_NAME, FAVORITES_DIR_NAME}
HISTORY_FILE = Path("history.txt")
HTML_TEMPLATE_FILE = "gala.html"
TEMPLATE_PATH = Path(__file__).with_name(HTML_TEMPLATE_FILE)
HTML_TEMPLATE = TEMPLATE_PATH.read_text(encoding="utf-8")
NO_MEDIA_HTML = '<p style="padding:2rem;color:#aaa">No media files found.</p>'


def is_in_excluded_media_folder(relative_path: Path) -> bool:
    return (
        bool(relative_path.parts) and relative_path.parts[0] in EXCLUDED_MEDIA_DIR_NAMES
    )


def list_media_files(base_dir: Path) -> list[str]:
    if not base_dir.is_dir():
        return []

    media_files: list[str] = []
    for dirpath, dirnames, filenames in os.walk(base_dir):
        current_dir = Path(dirpath)
        if current_dir == base_dir:
            dirnames[:] = [
                name for name in dirnames if name not in EXCLUDED_MEDIA_DIR_NAMES
            ]
        relative_dir = current_dir.relative_to(base_dir)
        media_files.extend(
            (relative_dir / name).as_posix()
            for name in filenames
            if Path(name).suffix.lower() in ALLOWED_EXTENSIONS
        )

    return sorted(media_files)


def create_media_item_html(filename: str) -> str:
    quoted_src = urllib.parse.quote(filename, safe="/")
    extension = Path(filename).suffix.lower()

    if extension in VIDEO_EXTENSIONS:
        media_tag = (
            f'<video data-src="{quoted_src}" controls muted playsinline '
            f'class="lazy-video" preload="none"></video>'
        )
    else:
        media_tag = (
            f'<a href="{quoted_src}" target="_blank" rel="noopener">'
            f'<img data-src="{quoted_src}" alt="" class="lazy-image" />'
            f"</a>"
        )

    return f'<div class="item" data-filename="{quoted_src}">{media_tag}</div>'


def generate_gallery_html(files: list[str]) -> bytes:
    items_html = (
        "\n".join(create_media_item_html(filename) for filename in files)
        if files
        else NO_MEDIA_HTML
    )

    return HTML_TEMPLATE.replace("{items_html}", items_html).encode("utf-8")


def save_path_to_history(path: str, history_file: Path = HISTORY_FILE) -> None:
    try:
        existing_paths = [
            value
            for value in history_file.read_text(encoding="utf-8").splitlines()
            if value.strip()
        ]
    except OSError:
        existing_paths = []

    updated_paths = [path] + [p for p in existing_paths if p != path]

    try:
        history_file.write_text("\n".join(updated_paths) + "\n", encoding="utf-8")
    except OSError:
        pass


class GalleryHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, directory: str | None = None, **kwargs):
        self.base_dir = Path(directory or Path.cwd()).resolve()
        super().__init__(*args, directory=str(self.base_dir), **kwargs)

    def do_GET(self) -> None:
        request_path = urllib.parse.urlparse(self.path).path
        if request_path == "/":
            self._serve_gallery()
            return

        super().do_GET()

    def do_DELETE(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        if parsed_url.path != "/api/delete":
            self.send_error(404, "Not Found")
            return

        filename = self._query_name_param(parsed_url)
        self._delete_file(filename)

    def do_POST(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        if parsed_url.path != "/api/favorite":
            self.send_error(404, "Not Found")
            return

        filename = self._query_name_param(parsed_url)
        self._favorite_file(filename)

    def _query_name_param(self, parsed_url: urllib.parse.ParseResult) -> str:
        query_params = urllib.parse.parse_qs(parsed_url.query)
        return query_params.get("name", [""])[0]

    def _serve_gallery(self) -> None:
        files = list_media_files(self.base_dir)
        content = generate_gallery_html(files)
        self._send_response(200, "text/html; charset=utf-8", content)

    def _delete_file(self, filename: str) -> None:
        resolved = self._resolve_supported_media_file(
            filename,
            "Only supported media files can be deleted",
        )
        if not resolved:
            return

        source_file, relative_path = resolved
        try:
            destination = self._build_delete_destination(source_file, relative_path)
            shutil.move(source_file, destination)
            self._send_json(200, {"ok": True})
        except PermissionError:
            self._send_json(403, {"ok": False, "error": "Permission denied"})
        except OSError as error:
            self._send_json(500, {"ok": False, "error": str(error)})

    def _favorite_file(self, filename: str) -> None:
        resolved = self._resolve_supported_media_file(
            filename,
            "Only supported media files can be favorited",
        )
        if not resolved:
            return

        source_file, relative_path = resolved
        try:
            destination = self._build_favorite_destination(relative_path)
            overwritten = destination.exists()
            shutil.copy2(source_file, destination)
            self._send_json(200, {"ok": True, "overwritten": overwritten})
        except PermissionError:
            self._send_json(403, {"ok": False, "error": "Permission denied"})
        except OSError as error:
            self._send_json(500, {"ok": False, "error": str(error)})

    def _resolve_supported_media_file(
        self, filename: str, unsupported_media_error: str
    ) -> tuple[Path, Path] | None:
        if not filename:
            self._send_json(400, {"ok": False, "error": "Missing filename"})
            return None

        source_file = (self.base_dir / filename).resolve()
        try:
            relative_path = source_file.relative_to(self.base_dir)
        except ValueError:
            self._send_json(403, {"ok": False, "error": "Invalid file path"})
            return None

        if is_in_excluded_media_folder(relative_path):
            self._send_json(403, {"ok": False, "error": "Invalid file path"})
            return None

        if not source_file.exists() or not source_file.is_file():
            self._send_json(404, {"ok": False, "error": "File not found"})
            return None

        if source_file.suffix.lower() not in ALLOWED_EXTENSIONS:
            self._send_json(400, {"ok": False, "error": unsupported_media_error})
            return None

        return source_file, relative_path

    def _build_delete_destination(self, source_file: Path, relative_path: Path) -> Path:
        deleted_dir = self.base_dir / DELETED_DIR_NAME
        destination = deleted_dir / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)

        if not destination.exists():
            return destination

        stem, suffix = source_file.stem, source_file.suffix
        n = 1
        while True:
            candidate = destination.parent / f"{stem}_{n}{suffix}"
            if not candidate.exists():
                return candidate
            n += 1

    def _build_favorite_destination(self, relative_path: Path) -> Path:
        favorites_dir = self.base_dir / FAVORITES_DIR_NAME
        destination = favorites_dir / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        return destination

    def _send_response(self, status: int, content_type: str, content: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_json(self, status: int, data: dict) -> None:
        content = json.dumps(data).encode("utf-8")
        self._send_response(status, "application/json; charset=utf-8", content)


def parse_args() -> argparse.Namespace:
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
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    base_directory = Path(args.directory).resolve()
    if not base_directory.is_dir():
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
