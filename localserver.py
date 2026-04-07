import os
import sys
import signal
import argparse
import logging
from http.server import SimpleHTTPRequestHandler, HTTPServer
from functools import partial

# --- Logging setup ---
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


class ImprovedHandler(SimpleHTTPRequestHandler):
    """HTTP handler with custom 404/500 pages and request logging."""

    def __init__(self, *args, directory=None, **kwargs):
        self.serve_directory = directory or os.getcwd()
        super().__init__(*args, directory=self.serve_directory, **kwargs)

    # ------------------------------------------------------------------ #
    #  Error pages                                                         #
    # ------------------------------------------------------------------ #

    def send_error_page(self, code, title, message):
        body = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{code} {title}</title>
  <style>
    body {{ font-family: sans-serif; display: flex; flex-direction: column;
            align-items: center; justify-content: center; height: 100vh; margin: 0;
            background: #f5f5f5; color: #333; }}
    h1   {{ font-size: 5rem; margin: 0; color: #e74c3c; }}
    p    {{ font-size: 1.2rem; }}
    a    {{ color: #3498db; text-decoration: none; }}
  </style>
</head>
<body>
  <h1>{code}</h1>
  <h2>{title}</h2>
  <p>{message}</p>
  <a href="/">← Back to home</a>
</body>
</html>""".encode()

        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_error(self, code, message=None, explain=None):
        error_messages = {
            400: ("Bad Request",        "The server could not understand your request."),
            403: ("Forbidden",          "You don't have permission to access this resource."),
            404: ("Page Not Found",     "The page you're looking for doesn't exist."),
            500: ("Server Error",       "Something went wrong on the server."),
            503: ("Service Unavailable","The server is temporarily unavailable."),
        }
        title, body_msg = error_messages.get(code, ("Error", message or "An error occurred."))
        try:
            self.send_error_page(code, title, body_msg)
        except Exception:
            # Fall back to the default handler if our custom page also fails
            super().send_error(code, message, explain)

    # ------------------------------------------------------------------ #
    #  Request logging                                                     #
    # ------------------------------------------------------------------ #

    def log_message(self, fmt, *args):
        status = args[1] if len(args) > 1 else "???"
        level  = logging.WARNING if str(status).startswith(("4", "5")) else logging.INFO
        logger.log(level, f"{self.client_address[0]} - {fmt % args}")

    # ------------------------------------------------------------------ #
    #  Safe GET with exception handling                                    #
    # ------------------------------------------------------------------ #

    def do_GET(self):
        try:
            super().do_GET()
        except BrokenPipeError:
            pass          # Client disconnected — ignore silently
        except Exception as exc:
            logger.error(f"Unhandled error serving {self.path}: {exc}")
            try:
                self.send_error(500)
            except Exception:
                pass


# ------------------------------------------------------------------ #
#  Server setup & graceful shutdown                                    #
# ------------------------------------------------------------------ #

def find_free_port(start_port):
    """Try ports starting at start_port until one is free."""
    import socket
    port = start_port
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("localhost", port)) != 0:
                return port   # Port is free
        logger.warning(f"Port {port} is in use, trying {port + 1}…")
        port += 1


def run(host, port, directory, auto_port):
    if auto_port:
        port = find_free_port(port)

    handler = partial(ImprovedHandler, directory=directory)

    try:
        server = HTTPServer((host, port), handler)
    except PermissionError:
        logger.error(f"Permission denied — cannot bind to port {port}. "
                     "Try a port above 1024 or run with elevated privileges.")
        sys.exit(1)
    except OSError as exc:
        logger.error(f"Could not start server: {exc}")
        sys.exit(1)

    abs_dir = os.path.abspath(directory)

    # Get local IP address
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
    except Exception:
        local_ip = "127.0.0.1"

    logger.info(f"Serving '{abs_dir}'")
    logger.info(f"Local:   http://localhost:{port}")
    logger.info(f"Network: http://{local_ip}:{port}")
    logger.info("Press Ctrl+C to stop.")

    # Graceful Ctrl+C / SIGTERM shutdown
    import threading
    def _shutdown(sig, frame):
        logger.info("Shutting down server")
        threading.Thread(target=server.shutdown, daemon=True).start()
        sys.exit(0)
 
    signal.signal(signal.SIGINT,  _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)
 
    server.serve_forever()


# ------------------------------------------------------------------ #
#  Entry point                                                         #
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simple multi-page HTTP server")
    parser.add_argument("--host",      default="",          help="Host to bind (default: all interfaces)")
    parser.add_argument("--port",      default=8000, type=int, help="Port to listen on (default: 8000)")
    parser.add_argument("--dir",       default=".",         help="Directory to serve (default: current)")
    parser.add_argument("--auto-port", action="store_true", help="Auto-select a free port if chosen one is busy")
    args = parser.parse_args()

    if not os.path.isdir(args.dir):
        logger.error(f"Directory '{args.dir}' does not exist.")
        sys.exit(1)

    run(args.host, args.port, args.dir, args.auto_port)
