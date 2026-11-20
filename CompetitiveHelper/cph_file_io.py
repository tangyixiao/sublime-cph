import json
import os
import re
import subprocess


_STRING = r'"(?:[^"\\\n]|\\.)*"'
_STRINGS = r'((?:' + _STRING + r'\s*)+)'
_MARKER = re.compile(r'^#\s+\d+\s+(' + _STRING + r')')
_REDIRECT = re.compile(
    r'\bfreopen\s*\(\s*' + _STRINGS + r',\s*"([rwa])[^"]*"\s*,\s*(stdin|stdout)\s*\)'
)
_TEMPLATE = re.compile(
    r'\b(Judge_File|Local_File)\s*\(\s*' + _STRINGS + r'(?:,\s*(\d+)\s*)?\)\s*;'
)
_TOKEN = re.compile(
    r'\b(?:freopen|Judge_File|Local_File)\s*\(|' + _STRING + r"|'(?:[^'\\\n]|\\.)*'"
)


def _literal(strings):
    return "".join(json.loads(value) for value in re.findall(_STRING, strings))


def _preprocess(source, compiler, flags):
    completed = subprocess.run(
        [compiler] + list(flags) + ["-E", source],
        cwd=os.path.dirname(source), stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if completed.returncode != 0:
        raise ValueError("Could not detect file I/O:\n" + completed.stderr.decode("utf-8", "replace"))
    lines = []
    is_source = False
    for line in completed.stdout.decode("utf-8", "replace").splitlines():
        marker = _MARKER.match(line)
        if marker:
            is_source = _literal(marker[1]) == source
        elif is_source:
            lines.append(line)
    return "\n".join(lines)


def _detect_names(code):
    names = {"input": set(), "output": set()}
    for token in _TOKEN.finditer(code):
        if token[0].startswith(('"', "'")):
            continue
        redirect = _REDIRECT.match(code, token.start())
        if redirect is not None:
            filename, mode, stream = redirect.groups()
            if stream == "stdin" and mode == "r":
                names["input"].add(_literal(filename))
            if stream == "stdout" and mode in ("w", "a"):
                names["output"].add(_literal(filename))
        template = _TEMPLATE.match(code, token.start())
        if template is not None:
            kind, filename, index = template.groups()
            if kind == "Local_File" and index is None:
                continue
            prefix = _literal(filename) + (str(int(index)) if index is not None else "")
            names["input"].add(prefix + ".in")
            names["output"].add(prefix + ".out")

    for stream, paths in names.items():
        if len(paths) > 1:
            raise ValueError("Multiple {} file names; set input/output in io.json.".format(stream))
    return {stream: next(iter(paths), None) for stream, paths in names.items()}


def _validate(names):
    for stream, name in names.items():
        if name is None:
            continue
        if not isinstance(name, str) or not name or "\0" in name:
            raise ValueError("{} in io.json must be a relative file name or null.".format(stream))
        parts = name.replace("\\", "/").split("/")
        if any(part in ("", ".", "..") or ":" in part for part in parts):
            raise ValueError("CPH file I/O requires relative paths inside its working directory.")
    return names


def detect_file_io(source, sample_dir, compiler, flags):
    override = os.path.join(sample_dir, "io.json")
    if os.path.isfile(override):
        with open(override, encoding="utf-8") as stream:
            settings = json.load(stream)
        if not isinstance(settings, dict) or not settings.keys() <= {"input", "output"}:
            raise ValueError("io.json must contain input and/or output file names.")
        return _validate({key: settings.get(key) for key in ("input", "output")})

    with open(source, encoding="utf-8", errors="replace") as stream:
        code = stream.read()
    names = {"input": None, "output": None}
    if any(word in code for word in ("freopen", "Judge_File", "Local_File")):
        names = _detect_names(_preprocess(source, compiler, flags))
    return _validate(names)
