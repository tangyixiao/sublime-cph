import os
import shutil
import tempfile
import threading


EXTENSIONS = {"input": ".in", "answer": ".ans", "output": ".out"}
_write_lock = threading.Lock()


def sample_dir(source):
    source = os.path.realpath(source)
    return os.path.join(os.path.dirname(source), "cph", os.path.splitext(os.path.basename(source))[0])


def case_ids(directory):
    if not os.path.isdir(directory):
        return []
    return sorted(name[:-3] for name in os.listdir(directory)
                  if name.endswith(".in") and os.path.isfile(os.path.join(directory, name)))


def pair_files(inputs, answers):
    if len(inputs) != len(answers) or not inputs:
        raise ValueError("Select the same number of input and answer files.")
    if len(inputs) == 1:
        return [(inputs[0], answers[0])]

    def by_stem(paths):
        index = {}
        for path in paths:
            stem = os.path.splitext(os.path.basename(path))[0]
            if stem in index:
                raise ValueError("More than one selected file has the name " + stem)
            index[stem] = path
        return index

    input_index, answer_index = by_stem(inputs), by_stem(answers)
    if input_index.keys() != answer_index.keys():
        raise ValueError("For batch import, each answer must have the same base name as its input.")
    return [(input_index[stem], answer_index[stem]) for stem in sorted(input_index)]


def add_case(directory, input_path=None, answer_path=None):
    os.makedirs(directory, exist_ok=True)
    with _write_lock, tempfile.TemporaryDirectory(dir=directory) as temporary:
        number = 1
        while any(os.path.exists(os.path.join(directory, "custom_{}".format(number) + extension))
                  for extension in EXTENSIONS.values()):
            number += 1
        case = "custom_{}".format(number)
        for extension, original in ((".in", input_path), (".ans", answer_path)):
            destination = os.path.join(temporary, case + extension)
            if original is None:
                with open(destination, "wb"):
                    pass
            else:
                shutil.copyfile(original, destination)
        # A case becomes visible as soon as its .in file exists.
        for extension in (".ans", ".in"):
            name = case + extension
            os.replace(os.path.join(temporary, name), os.path.join(directory, name))
    return case


def preview(path, limit=4096, max_lines=16):
    try:
        with open(path, "rb") as stream:
            data = stream.read(limit + 1)
    except FileNotFoundError:
        return None, False
    lines = data[:limit].decode("utf-8", "replace").splitlines()
    return "\n".join(lines[:max_lines]), len(data) > limit or len(lines) > max_lines
