import json
import os
import re
import shutil


_UNSAFE_NAME = re.compile(r"[\\/:\x00-\x1f]")
_FALLBACK_TEMPLATE = "#include <bits/stdc++.h>\nusing namespace std;\n\nint main() {\n    ios::sync_with_stdio(false);\n    cin.tie(nullptr);\n    return 0;\n}\n"


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
    safe_name = slugify(data.get("name", "problem"))
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
