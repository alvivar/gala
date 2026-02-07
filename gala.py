import argparse
import html
import json
import os
import shutil
import sys
import urllib.parse
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from itertools import count
from pathlib import Path


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif"}
VIDEO_EXTENSIONS = {".webm", ".mp4"}
ALLOWED_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS
DELETED_DIR_NAME = "deleted"
FAVORITES_DIR_NAME = "favorites"
EXCLUDED_MEDIA_DIR_NAMES = {DELETED_DIR_NAME, FAVORITES_DIR_NAME}
HISTORY_FILE = Path("history.txt")
HTML_TEMPLATE_FILE = "gala.html"
NO_MEDIA_HTML = '<p style="padding:2rem;color:#aaa">No media files found.</p>'


def is_supported_media_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS


def is_in_excluded_media_folder(relative_path: Path) -> bool:
    return (
        bool(relative_path.parts)
        and relative_path.parts[0] in EXCLUDED_MEDIA_DIR_NAMES
    )


def list_media_files(base_dir: Path) -> list[str]:
    try:
        media_files: list[str] = []
        for entry in base_dir.rglob("*"):
            if not is_supported_media_file(entry):
                continue

            relative_path = entry.relative_to(base_dir)
            if is_in_excluded_media_folder(relative_path):
                continue

            media_files.append(relative_path.as_posix())

        return sorted(media_files)
    except FileNotFoundError:
        return []


def create_media_item_html(filename: str) -> str:
    safe_name = html.escape(filename, quote=True)
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

    return (
        f'<div class="item" data-name="{safe_name}" '
        f'data-filename="{quoted_src}">{media_tag}</div>'
    )


def load_html_template() -> str:
    template_path = Path(__file__).parent / HTML_TEMPLATE_FILE
    return template_path.read_text(encoding="utf-8")


def generate_gallery_html(files: list[str]) -> bytes:
    items_html = (
        "\n".join(create_media_item_html(filename) for filename in files)
        if files
        else NO_MEDIA_HTML
    )

    html_document = load_html_template().replace("{items_html}", items_html)
    return html_document.encode("utf-8")


def save_path_to_history(path: str, history_file: Path = HISTORY_FILE) -> None:
    existing_paths: list[str] = []

    if history_file.exists():
        try:
            existing_paths = [
                value
                for value in history_file.read_text(encoding="utf-8").splitlines()
                if value.strip()
            ]
        except OSError:
            pass

    if path in existing_paths:
        existing_paths.remove(path)

    updated_paths = [path, *existing_paths]

    try:
        history_file.write_text("\n".join(updated_paths) + "\n", encoding="utf-8")
    except OSError:
        pass


class GalleryHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, directory: str | None = None, **kwargs):
        self.base_dir = Path(directory or os.getcwd()).resolve()
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

        query_params = urllib.parse.parse_qs(parsed_url.query)
        filename = next(iter(query_params.get("name", [])), "")
        self._delete_file(filename)

    def do_POST(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        if parsed_url.path != "/api/favorite":
            self.send_error(404, "Not Found")
            return

        query_params = urllib.parse.parse_qs(parsed_url.query)
        filename = next(iter(query_params.get("name", [])), "")
        self._favorite_file(filename)

    def _serve_gallery(self) -> None:
        files = list_media_files(self.base_dir)
        content = generate_gallery_html(files)
        self._send_response(200, "text/html; charset=utf-8", content)

    def _delete_file(self, filename: str) -> None:
        if not filename:
            self._send_json(400, {"ok": False, "error": "Missing filename"})
            return

        try:
            source_file, relative_path = self._resolve_source_file(filename)
            destination = self._build_delete_destination(source_file, relative_path)

            shutil.move(source_file, destination)
            self._send_json(200, {"ok": True})
        except ValueError:
            self._send_json(403, {"ok": False, "error": "Invalid file path"})
        except FileNotFoundError:
            self._send_json(404, {"ok": False, "error": "File not found"})
        except PermissionError:
            self._send_json(403, {"ok": False, "error": "Permission denied"})
        except Exception as error:
            self._send_json(500, {"ok": False, "error": str(error)})

    def _favorite_file(self, filename: str) -> None:
        if not filename:
            self._send_json(400, {"ok": False, "error": "Missing filename"})
            return

        try:
            source_file, relative_path = self._resolve_source_file(filename)

            if is_in_excluded_media_folder(relative_path):
                self._send_json(400, {"ok": False, "error": "Invalid file path"})
                return

            if not source_file.exists() or not source_file.is_file():
                self._send_json(404, {"ok": False, "error": "File not found"})
                return

            if source_file.suffix.lower() not in ALLOWED_EXTENSIONS:
                self._send_json(
                    400,
                    {
                        "ok": False,
                        "error": "Only supported media files can be favorited",
                    },
                )
                return

            destination = self._build_favorite_destination(relative_path)
            overwritten = destination.exists()
            shutil.copy2(source_file, destination)
            self._send_json(200, {"ok": True, "overwritten": overwritten})
        except ValueError:
            self._send_json(403, {"ok": False, "error": "Invalid file path"})
        except PermissionError:
            self._send_json(403, {"ok": False, "error": "Permission denied"})
        except Exception as error:
            self._send_json(500, {"ok": False, "error": str(error)})

    def _resolve_source_file(self, filename: str) -> tuple[Path, Path]:
        source_file = (self.base_dir / urllib.parse.unquote(filename)).resolve()
        relative_path = source_file.relative_to(self.base_dir)
        return source_file, relative_path

    def _build_delete_destination(self, source_file: Path, relative_path: Path) -> Path:
        deleted_dir = self.base_dir / DELETED_DIR_NAME
        destination = deleted_dir / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)

        if not destination.exists():
            return destination

        stem, suffix = source_file.stem, source_file.suffix
        for index in count(1):
            candidate = destination.parent / f"{stem}_{index}{suffix}"
            if not candidate.exists():
                return candidate

        raise RuntimeError("Could not determine destination filename")

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
