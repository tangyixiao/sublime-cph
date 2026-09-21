import argparse
import difflib
import hashlib
import os
import subprocess
import sys
import tempfile
import time
try:
    from pathlib import Path
except ImportError:
    # Sublime Text 4's legacy Python 3.3 plugin host imports every .py file
    # in a package. The runner itself executes with the system Python, where
    # pathlib is available; keeping this import optional lets Sublime load the
    # package without trying to execute the runner as a plugin.
    Path = None


DEFAULT_FLAGS = ("-std=c++20", "-Wall", "-Wextra", "-O2", "-pipe")


def binary_path(source):
    source = Path(source).resolve()
    digest = hashlib.sha1(str(source).encode("utf-8")).hexdigest()[:12]
    output_dir = Path(tempfile.gettempdir()) / "sublime-cph"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / (source.stem + "-" + digest)


def compile_program(source, compiler="c++", flags=DEFAULT_FLAGS):
    source = Path(source).resolve()
    binary = binary_path(source)
    command = [compiler] + list(flags) + [str(source), "-o", str(binary)]
    result = subprocess.run(command, cwd=str(source.parent), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return binary, result


def normalize_output(value):
    text = value.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.rstrip() for line in text.split("\n")).rstrip()


def _run_case(binary, input_data, timeout):
    started = time.monotonic()
    process = subprocess.Popen(
        [str(binary)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    try:
        stdout, stderr = process.communicate(input=input_data.encode("utf-8"), timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
        return {
            "status": "TLE",
            "elapsed": time.monotonic() - started,
            "output": stdout.decode("utf-8", "replace"),
            "error": stderr.decode("utf-8", "replace"),
        }

    output = stdout.decode("utf-8", "replace")
    error = stderr.decode("utf-8", "replace")
    if process.returncode != 0:
        status = "RTE"
    else:
        status = "OK"
    return {
        "status": status,
        "elapsed": time.monotonic() - started,
        "output": output,
        "error": error,
    }


def run_samples(source, sample_dir, compiler="c++", timeout=3):
    source = Path(source).resolve()
    sample_dir = Path(sample_dir).resolve()
    binary, compile_result = compile_program(source, compiler=compiler)
    report = {
        "compiled": compile_result.returncode == 0,
        "compile_stdout": compile_result.stdout.decode("utf-8", "replace"),
        "compile_stderr": compile_result.stderr.decode("utf-8", "replace"),
        "passed": 0,
        "failed": 0,
        "cases": [],
    }
    if compile_result.returncode != 0:
        return report

    for input_path in sorted(sample_dir.glob("*.in")):
        answer_path = input_path.with_suffix(".ans")
        input_data = input_path.read_text(encoding="utf-8")
        expected = answer_path.read_text(encoding="utf-8") if answer_path.is_file() else ""
        case = _run_case(binary, input_data, timeout)
        if case["status"] not in ("TLE", "RTE"):
            case["status"] = "AC" if normalize_output(case["output"]) == normalize_output(expected) else "WA"
        case["name"] = input_path.name
        case["expected"] = expected
        (input_path.with_suffix(".out")).write_text(case["output"], encoding="utf-8")
        report["cases"].append(case)
        if case["status"] == "AC":
            report["passed"] += 1
        else:
            report["failed"] += 1
    return report


def _sample_dir_for(source):
    source = Path(source).resolve()
    return source.parent / "cph" / source.stem


def format_report(report):
    lines = []
    if not report["compiled"]:
        lines.append("COMPILE ERROR")
        lines.append(report["compile_stderr"].rstrip())
        return "\n".join(lines)
    for case in report["cases"]:
        lines.append("{} {} ({:.3f}s)".format(case["status"], case["name"], case["elapsed"]))
        if case["status"] == "WA":
            diff = difflib.unified_diff(
                case["expected"].splitlines(), case["output"].splitlines(),
                fromfile="expected", tofile="actual", lineterm=""
            )
            lines.extend(diff)
        if case["error"]:
            lines.append(case["error"].rstrip())
    lines.append("{} passed, {} failed".format(report["passed"], report["failed"]))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Compile and test C++ files for Sublime CPH")
    parser.add_argument("action", choices=("compile", "run", "test"))
    parser.add_argument("source")
    parser.add_argument("--compiler", default="c++")
    parser.add_argument("--timeout", type=float, default=3.0)
    args = parser.parse_args(argv)
    source = Path(args.source).resolve()
    if args.action == "compile":
        _, result = compile_program(source, compiler=args.compiler)
        sys.stdout.write(result.stdout.decode("utf-8", "replace"))
        sys.stderr.write(result.stderr.decode("utf-8", "replace"))
        return result.returncode
    if args.action == "test":
        report = run_samples(source, _sample_dir_for(source), compiler=args.compiler, timeout=args.timeout)
        print(format_report(report))
        return 0 if report["compiled"] and report["failed"] == 0 else 1

    binary, result = compile_program(source, compiler=args.compiler)
    if result.returncode != 0:
        sys.stderr.write(result.stderr.decode("utf-8", "replace"))
        return result.returncode
    sample_input = _sample_dir_for(source) / "input.txt"
    input_data = sample_input.read_text(encoding="utf-8") if sample_input.is_file() else ""
    completed = subprocess.run(
        [str(binary)],
        input=input_data.encode("utf-8"),
        cwd=str(source.parent),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    sample_dir = _sample_dir_for(source)
    sample_dir.mkdir(parents=True, exist_ok=True)
    (sample_dir / "output.txt").write_bytes(completed.stdout)
    sys.stdout.write(completed.stdout.decode("utf-8", "replace"))
    sys.stderr.write(completed.stderr.decode("utf-8", "replace"))
    return completed.returncode


if __name__ == "__main__":
    sys.exit(main())
