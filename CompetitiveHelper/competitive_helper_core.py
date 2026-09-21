import json
import re
import shutil
from pathlib import Path


_UNSAFE_NAME = re.compile(r"[\\/:\x00-\x1f]")
_FALLBACK_TEMPLATE = "#include <bits/stdc++.h>\nusing namespace std;\n\nint main() {\n    ios::sync_with_stdio(false);\n    cin.tie(nullptr);\n    return 0;\n}\n"


def slugify(name):
    """Make a problem name safe to use as a local file/directory name."""
    value = _UNSAFE_NAME.sub("_", str(name or "problem"))
    value = value.strip(" .")
    return value or "problem"


def import_problem(data, code_root, template_path):
    """Persist a Competitive Companion payload and return created paths."""
    root = Path(code_root).expanduser()
    template = Path(template_path).expanduser()
    safe_name = slugify(data.get("name", "problem"))
    sample_dir = root / "cph" / safe_name
    source = root / (safe_name + ".cpp")
    sample_dir.mkdir(parents=True, exist_ok=True)
    root.mkdir(parents=True, exist_ok=True)

    if not source.exists():
        if template.is_file():
            shutil.copyfile(str(template), str(source))
        else:
            source.write_text(_FALLBACK_TEMPLATE, encoding="utf-8")

    tests = data.get("tests") or []
    for index, test in enumerate(tests, 1):
        input_data = str(test.get("input", ""))
        expected = str(test.get("output", ""))
        (sample_dir / (safe_name + "_{}.in".format(index))).write_text(input_data, encoding="utf-8")
        (sample_dir / (safe_name + "_{}.ans".format(index))).write_text(expected, encoding="utf-8")

    first_input = str(tests[0].get("input", "")) if tests else ""
    first_expected = str(tests[0].get("output", "")) if tests else ""
    (sample_dir / "input.txt").write_text(first_input, encoding="utf-8")
    (sample_dir / "expected.txt").write_text(first_expected, encoding="utf-8")
    (sample_dir / "output.txt").write_text("", encoding="utf-8")
    (sample_dir / "problem.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    return {
        "name": safe_name,
        "source": source,
        "sample_dir": sample_dir,
        "test_count": len(tests),
    }
