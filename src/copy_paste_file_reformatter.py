import sys
from pathlib import Path
from typing import Tuple, List


def read_copy_paste_file(filename: Path):
    with open(filename, 'r') as f:
        file_contents = [l.strip() for l in f.readlines()]
    members = list()
    for bungie, discord in zip(file_contents[0::2], file_contents[1::2]):
        members.append((bungie, discord))
    return members


def write_csv_file(filename: Path, data: List[Tuple[str, str]]):
    with open(filename, "w") as out:
        _write_line(out, ("# Destiny user name", "Discord user name","Date left clan"))
        for line in data:
            _write_line(out, line + ("",))


def _write_line(out, fields):
    line = []
    for field in fields[:-1]:
        field_with_comma = field + ","
        line.append(f"{field_with_comma:30}")
    line.append(fields[-1])
    out.write("".join(line) + "\n")

def main():
    input_file = Path(sys.argv[1])
    data = read_copy_paste_file(input_file)
    output_path = Path(sys.argv[2])
    write_csv_file(output_path, data)


if __name__ == "__main__":
    main()
