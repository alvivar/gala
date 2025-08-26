# Gala

A simple Python server that recursively creates a web gallery for images and videos in any folder.

### Features

-   **Recursive gallery**: Serves all supported media under the chosen folder.
-   **Supported types**: Images (`.jpg`, `.jpeg`, `.png`, `.gif`) and videos (`.webm`, `.mp4`).
-   **Clean viewer**: One item per screen with scroll-snap for smooth navigation.
-   **Autoplay videos**: Videos play when in view and pause when out of view.
-   **Keyboard controls**: Navigate, play/pause, and delete files from disk.

### Requirements

-   **Python**: 3.10+ (standard library only; no external dependencies).

### Usage

```bash
python gala.py [DIRECTORY] [--host HOST] [--port PORT] [--no-open]
```

-   **DIRECTORY**: Folder to serve. Defaults to current directory (`.`).
-   **--host**: Bind host (default: `127.0.0.1`).
-   **--port**: Bind port (default: `8000`).
-   **--no-open**: Do not auto-open the browser on start.

#### Examples

```bash
# Serve current folder on http://127.0.0.1:8000 and open browser
python gala.py

# Serve a specific folder
python gala.py "D:\Photos"      # Windows
python gala.py ~/Pictures         # macOS/Linux

# Serve on all interfaces without opening a browser
python gala.py . --host 0.0.0.0 --port 8080 --no-open
```

When the server starts, you'll see a line like:

```
Serving /absolute/path/to/DIRECTORY at http://127.0.0.1:8000/
```

Press `Ctrl+C` in the terminal to stop the server.

### Keyboard shortcuts (in the browser)

-   **j**: Next item
-   **k**: Previous item
-   **n**: Random unviewed item (cycles through all before repeating)
-   **b**: Go back to previously viewed item
-   **Space**: Play/pause current video (if the item is a video)
-   **x**: Delete the current item from disk

Notes:

-   Clicking an image opens it in a new tab.
-   Deleting removes the file from your filesystem immediately.

### API

These endpoints are available while the server is running. Paths are relative to the served directory.

-   **GET /** → Gallery HTML page
-   **GET /api/list** → JSON list of media
    -   Response body: `{ "files": ["relative/path/to/file1.jpg", ...] }`
-   **DELETE /api/delete?name=RELATIVE_PATH** → Delete a file
-   **POST /api/delete** → Delete a file
    -   Body (JSON): `{ "name": "relative/path/to/file.jpg" }`
    -   or `application/x-www-form-urlencoded`: `name=relative/path/to/file.jpg`

Examples:

```bash
curl "http://127.0.0.1:8000/api/list"

curl -X DELETE "http://127.0.0.1:8000/api/delete?name=subdir%2Fphoto.jpg"

curl -X POST "http://127.0.0.1:8000/api/delete" \
  -H "Content-Type: application/json" \
  -d '{"name":"subdir/photo.jpg"}'
```

### Safety and security

-   **No authentication**: Anyone who can reach the server can delete files via the UI or API.
-   **Default is local-only**: By default it binds to `127.0.0.1`. Avoid exposing it to untrusted networks. If you bind to `0.0.0.0`, ensure your network is trusted.
-   **Permanent deletes**: Deletion uses the OS `unlink` and does not send files to a recycle bin.
-   **Relative paths**: The delete API expects a path relative to the served directory. Only use the UI or trusted scripts to call it.

### Troubleshooting

-   **Files not showing up?** Ensure extensions are supported. You can change them at the top of `gala.py` in `IMAGE_EXTENSIONS` and `VIDEO_EXTENSIONS`.
-   **Videos don’t play with sound automatically**: The viewer starts videos muted to allow autoplay. Use the built-in controls to unmute.
-   **Permission errors on delete**: Ensure the process has permission to modify files in the served directory.

### Development

-   Edit the sets near the top of `gala.py` to add or remove filetypes:
    -   `IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif"}`
    -   `VIDEO_EXTENSIONS = {".webm", ".mp4"}`
    -   `ALLOWED_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS`
