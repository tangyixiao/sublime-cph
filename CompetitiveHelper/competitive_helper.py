import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import sublime
import sublime_plugin

try:
    from . import competitive_helper_core
except (ImportError, ValueError):
    import competitive_helper_core


_server = None


class _ReusableHTTPServer(HTTPServer):
    allow_reuse_address = True


def _settings():
    return sublime.load_settings("CompetitiveHelper.sublime-settings")


def _start_listener(show_error=True):
    global _server
    if _server is not None:
        print("CompetitiveHelper: listener already running")
        return True
    port = int(_settings().get("port", 10045))
    try:
        _server = _ReusableHTTPServer(("127.0.0.1", port), _RequestHandler)
    except OSError as error:
        message = "CompetitiveHelper cannot listen on port {}: {}".format(port, error)
        if show_error:
            sublime.error_message(message)
        else:
            print(message)
        return False
    thread = threading.Thread(target=_server.serve_forever)
    thread.daemon = True
    thread.start()
    print("CompetitiveHelper: listening on 127.0.0.1:{}".format(port))
    return True


def _json_response(handler, status, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class _RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            _json_response(self, 200, {"ok": True, "service": "sublime-cph"})
        else:
            _json_response(self, 404, {"ok": False, "error": "not found"})

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 20 * 1024 * 1024:
                raise ValueError("invalid request size")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            settings = _settings()
            result = competitive_helper_core.import_problem(
                payload,
                settings.get("code_root", "~/Code"),
                settings.get("template_path", "~/Code/template.cpp"),
            )
            response = {
                "ok": True,
                "source": str(result["source"]),
                "sample_dir": str(result["sample_dir"]),
                "test_count": result["test_count"],
            }
            _json_response(self, 200, response)
            if settings.get("open_source", True):
                sublime.set_timeout(lambda: sublime.active_window().open_file(str(result["source"])), 0)
        except Exception as error:
            _json_response(self, 400, {"ok": False, "error": str(error)})

    def log_message(self, format_string, *args):
        print("CompetitiveHelper: " + format_string % args)


class StartCphListenerCommand(sublime_plugin.ApplicationCommand):
    def run(self):
        _start_listener(show_error=True)


class StopCphListenerCommand(sublime_plugin.ApplicationCommand):
    def run(self):
        global _server
        if _server is None:
            return
        _server.shutdown()
        _server.server_close()
        _server = None
        print("CompetitiveHelper: listener stopped")


class FormatCphFileCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        filename = self.view.file_name()
        if not filename:
            sublime.error_message("CompetitiveHelper: save the file before formatting")
            return
        program = _settings().get("clang_format_program", "clang-format")
        try:
            formatted = competitive_helper_core.format_cpp(
                self.view.substr(sublime.Region(0, self.view.size())),
                filename,
                program=program,
            )
        except (OSError, RuntimeError) as error:
            sublime.error_message("CompetitiveHelper clang-format: {}".format(error))
            return
        self.view.replace(edit, sublime.Region(0, self.view.size()), formatted)


def plugin_loaded():
    if _settings().get("auto_start", True):
        sublime.set_timeout(lambda: _start_listener(show_error=False), 0)
