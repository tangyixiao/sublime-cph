import argparse
from contextlib import ExitStack
import difflib
import hashlib
from itertools import islice
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

try:
    from pathlib import Path
except ImportError:
    # The legacy Sublime plugin host imports the module, but the runner uses system Python.
    Path = None

try:
    from .cph_file_io import detect_file_io
except (ImportError, ValueError):
    from cph_file_io import detect_file_io


DEFAULT_FLAGS = ("-std=c++20", "-Wall", "-Wextra", "-O2", "-pipe")
EXE_SUFFIX = ".exe" if os.name == "nt" else ""


def binary_path(source):
    source = Path(source).resolve()
    digest = hashlib.sha1(str(source).encode("utf-8")).hexdigest()[:12]
    output_dir = Path(tempfile.gettempdir()) / "sublime-cph"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / (source.stem + "-" + digest + EXE_SUFFIX)


def compile_program(source, compiler="c++", flags=DEFAULT_FLAGS, binary=None):
    source = Path(source).resolve()
    binary = binary if binary is not None else binary_path(source)
    command = [compiler] + list(flags) + [str(source), "-o", str(binary)]
    result = subprocess.run(command, cwd=str(source.parent), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return binary, result


def normalize_output(value):
    text = value.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.rstrip() for line in text.split("\n")).rstrip()


def _run_case(binary, input_path, timeout, working_dir, file_io):
    started = time.monotonic()
    output_path = None
    with ExitStack() as stack:
        if file_io["input"] or file_io["output"]:
            working_dir = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        if file_io["input"]:
            staged = working_dir / file_io["input"]
            staged.parent.mkdir(parents=True, exist_ok=True)
            if input_path is None:
                staged.touch()
            else:
                shutil.copyfile(str(input_path), str(staged))
        if file_io["output"]:
            output_path = working_dir / file_io["output"]
            output_path.parent.mkdir(parents=True, exist_ok=True)
        stdin = subprocess.DEVNULL if input_path is None else stack.enter_context(input_path.open("rb"))
        process = subprocess.Popen(
            [str(binary)], stdin=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=str(working_dir)
        )
        status = "OK"
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            status = "TLE"
        if status == "OK" and process.returncode != 0:
            status = "RTE"
        if output_path is not None:
            if output_path.is_file():
                stdout = output_path.read_bytes()
            elif status == "OK":
                status = "NO OUTPUT"
                stderr += ("\nMissing output file: " + file_io["output"]).encode("utf-8")

    return {
        "status": status,
        "elapsed": time.monotonic() - started,
        "output": stdout.decode("utf-8", "replace"),
        "error": stderr.decode("utf-8", "replace"),
        "returncode": process.returncode,
    }


def run_samples(source, sample_dir, compiler="c++", timeout=3, case_id=None):
    source = Path(source).resolve()
    sample_dir = Path(sample_dir).resolve()
    inputs = [path for path in sorted(sample_dir.glob("*.in"))
              if case_id is None or path.stem == case_id]
    if case_id is not None and not inputs:
        raise ValueError("Sample not found: {}".format(case_id))
    with tempfile.TemporaryDirectory() as temporary:
        binary = Path(temporary) / ("program" + EXE_SUFFIX)
        return _test_with_binary(source, sample_dir, inputs, binary, compiler, timeout)


def _test_with_binary(source, sample_dir, inputs, binary, compiler, timeout):
    _, compile_result = compile_program(source, compiler=compiler, binary=binary)
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

    file_io = detect_file_io(str(source), str(sample_dir), compiler, DEFAULT_FLAGS)
    report["file_io"] = file_io
    for input_path in inputs:
        answer_path = input_path.with_suffix(".ans")
        expected = answer_path.read_text(encoding="utf-8", errors="replace") if answer_path.is_file() else None
        case = _run_case(binary, input_path, timeout, source.parent, file_io)
        case["name"] = input_path.name
        case["expected"] = expected
        input_path.with_suffix(".out").write_text(case["output"], encoding="utf-8")
        if case["status"] == "OK":
            if expected is None:
                case["status"] = "NO ANSWER"
            else:
                case["status"] = "AC" if normalize_output(case["output"]) == normalize_output(expected) else "WA"
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
    if not report["compiled"]:
        return "COMPILE ERROR\n" + report["compile_stderr"].rstrip()
    lines = []
    file_io = report.get("file_io", {})
    if file_io.get("input") or file_io.get("output"):
        lines.append("I/O: {} → {}".format(file_io.get("input") or "stdin", file_io.get("output") or "stdout"))
    if not report["cases"]:
        lines.append("No samples found.")
    for case in report["cases"]:
        lines.append("{} {} ({:.3f}s)".format(case["status"], case["name"], case["elapsed"]))
        if case["status"] == "WA":
            if len(case["expected"]) + len(case["output"]) <= 65536:
                diff = difflib.unified_diff(
                    case["expected"].splitlines(), case["output"].splitlines(),
                    fromfile="expected", tofile="actual", lineterm=""
                )
                lines.extend(line[:240] for line in islice(diff, 40))
            else:
                lines.append("Open the .ans and .out files to inspect the full output.")
        if case["error"]:
            lines.append(case["error"][:4000].rstrip())
    lines.append("{} passed, {} failed".format(report["passed"], report["failed"]))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Compile and test C++ files for Sublime CPH")
    parser.add_argument("action", choices=("compile", "run", "test"))
    parser.add_argument("source")
    parser.add_argument("--compiler", default="c++")
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("--case")
    parser.add_argument("--json-report", action="store_true")
    args = parser.parse_args(argv)
    source = Path(args.source).resolve()
    try:
        return _run_action(args, source)
    except (OSError, ValueError) as error:
        if args.json_report:
            print(json.dumps({"cases": [], "log": str(error)}))
        else:
            print("Competitive Helper: {}".format(error), file=sys.stderr)
        return 1


def _run_action(args, source):
    if args.action == "test":
        report = run_samples(
            source, _sample_dir_for(source), compiler=args.compiler, timeout=args.timeout, case_id=args.case
        )
        log = format_report(report)
        if args.json_report:
            print(json.dumps({
                "log": log[:8000],
                "cases": [{key: case[key] for key in ("name", "status", "elapsed")} for case in report["cases"]]
            }))
        else:
            print(log)
        return 0 if report["compiled"] and report["failed"] == 0 else 1

    if args.action == "compile":
        _, result = compile_program(source, compiler=args.compiler)
        sys.stdout.write(result.stdout.decode("utf-8", "replace"))
        sys.stderr.write(result.stderr.decode("utf-8", "replace"))
        return result.returncode

    with tempfile.TemporaryDirectory() as temporary:
        binary = Path(temporary) / ("program" + EXE_SUFFIX)
        _, result = compile_program(source, compiler=args.compiler, binary=binary)
        if result.returncode != 0:
            sys.stderr.write(result.stderr.decode("utf-8", "replace"))
            return result.returncode
        sample_dir = _sample_dir_for(source)
        sample_input = sample_dir / "input.txt"
        if not sample_input.is_file():
            sample_input = next(iter(sorted(sample_dir.glob("*.in"))), None)
        file_io = detect_file_io(str(source), str(sample_dir), args.compiler, DEFAULT_FLAGS)
        case = _run_case(binary, sample_input, args.timeout, source.parent, file_io)
    sample_dir.mkdir(parents=True, exist_ok=True)
    (sample_dir / "output.txt").write_text(case["output"], encoding="utf-8")
    sys.stdout.write(case["output"])
    sys.stderr.write(case["error"])
    if case["status"] == "TLE":
        print("Time limit exceeded.", file=sys.stderr)
    return case["returncode"] if case["status"] in ("OK", "RTE") else 1


if __name__ == "__main__":
    sys.exit(main())
