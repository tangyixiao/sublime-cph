import html
import json
import os
import subprocess
import threading

import sublime
import sublime_plugin

try:
    from . import cph_samples
except (ImportError, ValueError):
    import cph_samples


_panels = {}
_running = set()
_STYLE = """
<style>
body { padding: 1.3em; }
a { color: var(--bluish); }
.bar { padding-bottom: 0.5em; }
.case { padding: 0.25em 0; }
.code { padding: 0.55em; background-color: color(var(--background) blend(var(--foreground) 92%)); }
.ok { color: var(--greenish); }
.error { color: var(--redish); }
.muted { color: color(var(--foreground) alpha(0.62)); }
</style>
"""


def _link(label, source, action, **args):
    args.update({"source": source, "action": action})
    return '<a href="{}">{}</a>'.format(sublime.command_url("cph_sample_panel", args), html.escape(label))


def _code(text):
    content = html.escape(text.expandtabs(4)).replace(" ", "&#160;").replace("\n", "<br>")
    return '<div class="code"><code>{}</code></div>'.format(content)


def _render(source, selected, cases, log, results):
    directory = cph_samples.sample_dir(source)
    content = [
        "<body>", _STYLE, '<div class="bar">',
        _link("新建样例", source, "add"), "　",
        _link("导入文件对", source, "import"), "　",
        _link("测试全部", source, "test"), "　",
        _link("刷新", source, "show", case=selected), "</div>"
    ]
    if not cases:
        content.append('<p class="muted">暂无样例。</p>')
    if selected:
        content.extend(("<h3>{}</h3>".format(html.escape(selected)),
                        _link("测试这组", source, "test", case=selected)))
        for kind, label in (("input", "输入"), ("answer", "预期输出"), ("output", "程序输出")):
            extension = cph_samples.EXTENSIONS[kind]
            path = os.path.join(directory, selected + extension)
            preview, truncated = cph_samples.preview(path)
            title = _link(label, source, "open", case=selected, kind=kind) if preview is not None else label
            content.append("<p><b>{}</b></p>".format(title))
            if preview:
                content.append(_code(preview))
            else:
                content.append('<div class="muted">{}</div>'.format("暂无内容" if preview is None else "空"))
            if truncated:
                content.append('<div class="muted">预览已截断，点击标题打开完整文件。</div>')
    if log:
        content.extend(("<h3>测试结果</h3>", _code(log)))
    if cases:
        content.append("<h3>样例列表</h3>")
    for case in cases:
        status = results.get(case + ".in")
        link = _link(case, source, "show", case=case)
        if status:
            css = "ok" if status["status"] == "AC" else "error"
            link += '　<span class="{}">{} · {:.3f}s</span>'.format(
                css, html.escape(status["status"]), status["elapsed"]
            )
        content.append('<div class="case">{}</div>'.format(link))
    content.append("</body>")
    return "".join(content)


class CphSamplePanelCommand(sublime_plugin.WindowCommand):
    def run(self, action="show", source=None, case=None, kind=None):
        if source is None:
            view = self.window.active_view()
            source = view.file_name() if view else None
        if not source or not os.path.isfile(source) or os.path.splitext(source)[1].lower() not in (
            ".cpp", ".cc", ".cxx", ".c++", ".c"
        ):
            sublime.status_message("Competitive Helper: 请先打开已保存的 C++ 文件。")
            return
        source = os.path.realpath(source)
        directory = cph_samples.sample_dir(source)
        cases = cph_samples.case_ids(directory)
        if case is not None and case not in cases:
            sublime.status_message("Competitive Helper: 找不到这组样例。")
            return
        key = (self.window.id(), source)

        if action == "add":
            try:
                case = cph_samples.add_case(directory)
            except OSError as error:
                sublime.error_message(str(error))
                return
            self.show(source, case)
            self.window.open_file(os.path.join(directory, case + ".ans"))
            self.window.open_file(os.path.join(directory, case + ".in"))
        elif action == "import":
            self.import_files(source, directory)
        elif action == "open" and case is not None and kind in cph_samples.EXTENSIONS:
            self.window.open_file(os.path.join(directory, case + cph_samples.EXTENSIONS[kind]))
        elif action == "test":
            self.test(key, case)
        elif action == "refresh_after_save":
            if key in _panels:
                self.show(source, log="", cases_result=[], focus=False)
        else:
            self.show(source, case)

    def show(self, source, case=None, log=None, cases_result=None, focus=True):
        directory = cph_samples.sample_dir(source)
        cases = cph_samples.case_ids(directory)
        key = (self.window.id(), source)
        panel = _panels.get(key)
        if panel is None or panel["sheet"].window() is None:
            panel = {"sheet": None, "log": "", "results": {}, "case": None}
        if log is not None:
            panel["log"] = log
        if cases_result is not None:
            panel["results"] = {item["name"]: item for item in cases_result}
        case = case or panel["case"]
        if case not in cases:
            case = cases[0] if cases else None
        panel["case"] = case
        content = _render(source, case, cases, panel["log"], panel["results"])
        if panel["sheet"] is None:
            title = "CPH · " + os.path.splitext(os.path.basename(source))[0]
            panel["sheet"] = self.window.new_html_sheet(title, content)
            _panels[key] = panel
        else:
            panel["sheet"].set_contents(content)
        if focus:
            self.window.focus_sheet(panel["sheet"])

    def import_files(self, source, directory):
        def selected_inputs(inputs):
            if not inputs:
                return
            sublime.open_dialog(
                lambda answers: selected_answers(inputs, answers),
                file_types=[("选择预期输出文件", ["ans", "out", "txt"])],
                directory=os.path.dirname(inputs[0]), multi_select=True
            )

        def selected_answers(inputs, answers):
            if not answers:
                return

            def copy():
                try:
                    pairs = cph_samples.pair_files(inputs, answers)
                    imported = [cph_samples.add_case(directory, pair[0], pair[1]) for pair in pairs]
                except (OSError, ValueError) as error:
                    message = "Competitive Helper: {}".format(error)
                    sublime.set_timeout(lambda: sublime.error_message(message), 0)
                    return

                def done():
                    if self.window.is_valid():
                        self.show(source, imported[0])
                        sublime.status_message("Competitive Helper: 已导入 {} 组样例。".format(len(imported)))

                sublime.set_timeout(done, 0)

            threading.Thread(target=copy, daemon=True).start()

        sublime.open_dialog(selected_inputs, file_types=[("选择输入文件", ["in", "txt"])],
                            directory=os.path.dirname(source), multi_select=True)

    def test(self, key, case):
        source = key[1]
        if key in _running:
            sublime.status_message("Competitive Helper: 正在测试。")
            return
        directory = cph_samples.sample_dir(source)
        if not cph_samples.case_ids(directory):
            self.show(source, log="暂无样例。")
            return
        for view in self.window.views():
            filename = view.file_name()
            if filename and view.is_dirty() and (os.path.realpath(filename) == source
                    or os.path.dirname(os.path.realpath(filename)) == directory):
                sublime.status_message("Competitive Helper: 请先保存源文件和样例。")
                return
        _running.add(key)
        self.show(source, case, log="正在测试…", cases_result=[])
        script = os.path.join(os.path.dirname(__file__), "cph_runner.py")
        command = ["python3", script, "test", source, "--json-report"]
        if case is not None:
            command.extend(("--case", case))

        def run_tests():
            try:
                process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = process.communicate()
                if not stdout:
                    raise ValueError(stderr.decode("utf-8", "replace").strip() or "测试进程没有返回结果。")
                report = json.loads(stdout.decode("utf-8"))
            except (OSError, ValueError) as error:
                report = {"log": str(error), "cases": []}

            def done():
                _running.discard(key)
                panel = _panels.get(key)
                if panel and panel["sheet"].window() is not None:
                    self.show(source, log=report["log"], cases_result=report["cases"], focus=False)

            sublime.set_timeout(done, 0)

        threading.Thread(target=run_tests, daemon=True).start()


class CphSampleSaveListener(sublime_plugin.EventListener):
    def on_post_save(self, view):
        if not view.file_name():
            return
        path = os.path.realpath(view.file_name())
        for key, panel in list(_panels.items()):
            window = panel["sheet"].window()
            if window is None:
                del _panels[key]
            elif path == key[1] or os.path.dirname(path) == cph_samples.sample_dir(key[1]):
                window.run_command("cph_sample_panel", {"action": "refresh_after_save", "source": key[1]})
