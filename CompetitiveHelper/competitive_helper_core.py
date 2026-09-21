import json
import os
import re
import shutil
from urllib.parse import urlparse


_UNSAFE_NAME = re.compile(r"[\\/:\x00-\x1f]")
_FALLBACK_TEMPLATE = "#include <bits/stdc++.h>\nusing namespace std;\n\nint main() {\n    ios::sync_with_stdio(false);\n    cin.tie(nullptr);\n    return 0;\n}\n"
_TEMPLATE_JS_UNSAFE_NAME = re.compile(r'[<>:"/\\|?*]')


def _is_host(hostname, expected):
    return hostname == expected or hostname.endswith("." + expected)


def _problem_id(name, url):
    """Port the problem-id rules from the user's template.js."""
    full_id = ""
    if url:
        try:
            parsed = urlparse(str(url))
            hostname = parsed.hostname or ""

            if _is_host(hostname, "codeforces.com"):
                patterns = (
                    r"/contest/(\d+)/problem/(\w+)",
                    r"/problemset/problem/(\d+)/(\w+)",
                    r"/gym/(\d+)/problem/(\w+)",
                )
                for pattern in patterns:
                    match = re.search(pattern, str(url))
                    if match:
                        full_id = "CF{}{}".format(match.group(1), match.group(2))
                        break

            if not full_id and _is_host(hostname, "luogu.com.cn"):
                match = re.search(r"problem/(\w+)", str(url))
                if match:
                    full_id = match.group(1)

            if not full_id and _is_host(hostname, "atcoder.jp"):
                match = re.search(r"tasks/(\w+)_(\w+)", str(url))
                if match:
                    full_id = "{}{}".format(
                        match.group(1).upper(), match.group(2).upper()
                    )

            if not full_id and _is_host(hostname, "poj.org"):
                match = re.search(r"[?&]id=(\d+)", str(url))
                if match:
                    full_id = "POJ{}".format(match.group(1))

            if not full_id and (
                _is_host(hostname, "uva.onlinejudge.org")
                or _is_host(hostname, "onlinejudge.org")
            ):
                match = re.search(r"/problem/(\d+)", str(url))
                if match:
                    full_id = "UVA{}".format(match.group(1))
        except (TypeError, ValueError):
            pass

    if not full_id:
        number = re.search(r"\d+", name)
        if number:
            full_id = number.group(0)
    return full_id


def _template_js_basename(data):
    """Return the .cpp basename produced by the user's template.js rules."""
    name = str(data.get("name", "problem") or "problem")
    full_id = _problem_id(name, data.get("url"))
    clean_name = _TEMPLATE_JS_UNSAFE_NAME.sub("_", name)

    if full_id.startswith("CF") and len(full_id) > 2:
        last_char = full_id[-1]
        prefix_match = re.match(r"^([A-Za-z])\.\s*", clean_name)
        if prefix_match and prefix_match.group(1).upper() == last_char.upper():
            clean_name = clean_name[len(prefix_match.group(0)) :]

    if full_id and clean_name.startswith(full_id):
        rest = clean_name[len(full_id) :]
        rest = re.sub(r"^[\s.\-_]+", "", rest)
        if rest:
            clean_name = rest

    if full_id:
        basename = "{} {}".format(full_id, clean_name) if clean_name else full_id
    else:
        basename = clean_name
    return slugify(basename)


def slugify(name):
    """Make a problem name safe to use as a local file/directory name."""
    value = _UNSAFE_NAME.sub("_", str(name or "problem"))
    value = value.strip(" .")
    return value or "problem"


def _ensure_dir(path):
    try:
        os.makedirs(path)
    except OSError:
        if not os.path.isdir(path):
            raise


def import_problem(data, code_root, template_path):
    """Persist a Competitive Companion payload and return created paths."""
    root = os.path.abspath(os.path.expanduser(str(code_root)))
    template = os.path.abspath(os.path.expanduser(str(template_path)))
    safe_name = _template_js_basename(data)
    sample_dir = os.path.join(root, "cph", safe_name)
    source = os.path.join(root, safe_name + ".cpp")
    _ensure_dir(sample_dir)
    _ensure_dir(root)

    if not os.path.isfile(source):
        if os.path.isfile(template):
            shutil.copyfile(template, source)
        else:
            with open(source, "w", encoding="utf-8") as solution_file:
                solution_file.write(_FALLBACK_TEMPLATE)

    tests = data.get("tests") or []
    for index, test in enumerate(tests, 1):
        input_data = str(test.get("input", ""))
        expected = str(test.get("output", ""))
        with open(os.path.join(sample_dir, safe_name + "_{}.in".format(index)), "w", encoding="utf-8") as input_file:
            input_file.write(input_data)
        with open(os.path.join(sample_dir, safe_name + "_{}.ans".format(index)), "w", encoding="utf-8") as answer_file:
            answer_file.write(expected)

    first_input = str(tests[0].get("input", "")) if tests else ""
    first_expected = str(tests[0].get("output", "")) if tests else ""
    with open(os.path.join(sample_dir, "input.txt"), "w", encoding="utf-8") as input_file:
        input_file.write(first_input)
    with open(os.path.join(sample_dir, "expected.txt"), "w", encoding="utf-8") as expected_file:
        expected_file.write(first_expected)
    with open(os.path.join(sample_dir, "output.txt"), "w", encoding="utf-8") as output_file:
        output_file.write("")
    with open(os.path.join(sample_dir, "problem.json"), "w", encoding="utf-8") as problem_file:
        problem_file.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")

    return {
        "name": safe_name,
        "source": source,
        "sample_dir": sample_dir,
        "test_count": len(tests),
    }
