import os
import sys
import subprocess
import re

assignable_types = [
    int,
    float,
    complex,
    bool,
    str,
    list,
    tuple,
    set,
    frozenset,
    dict,
    bytes,
    bytearray
]

enforce_text = """
from functools import wraps
import inspect

def check_type(value: type, expected: type) -> None:
    if isinstance(expected, tuple):
        for t in expected:
            check_type(value, t)
        return None
    
    origin = getattr(expected, '__origin__', None)
    args = getattr(expected, '__args__', None)
    
    if origin in (list,):
        if not isinstance(value, list): raise TypeError(f"expected {expected.__name__}, got {type(value).__name__}")
        if args: 
            for v in value:
                check_type(v, args[0])
        return None
    
    elif origin in (dict,):
        if not isinstance(value, dict): raise TypeError(f"expected {expected.__name__}, got {type(value).__name__}")
        if args and len(args) == 2:
            for k, v in value.items():
                check_type(k, args[0])
                check_type(v, args[1])
        return None
    
    elif origin in (tuple,):
        if not isinstance(value, tuple): raise TypeError(f"expected {expected.__name__}, got {type(value).__name__}")
        if args:
            if len(args) != len(value): raise TypeError(f"expected {expected.__name__}, got {type(value).__name__}")
            for v, t in zip(value, args):
                check_type(v, t)
        return None
    
    elif origin in (set,):
        if not isinstance(value, set): raise TypeError(f"expected {expected.__name__}, got {type(value).__name__}")
        if args: 
            for v in value:
                check_type(v, args[0])
        return None
    
    if not isinstance(value, expected):
        raise TypeError(f"expected {expected.__name__}, got {type(value).__name__}")
    return None


def enforce_wrapper(func) -> object:
    sig = inspect.signature(func)
    annotations = func.__annotations__

    @wraps(func)
    def wrapper(*args, **kwargs) -> object:
        bound = sig.bind_partial(*args, **kwargs)
        bound.apply_defaults()

        for name, value in bound.arguments.items():
            if name in annotations:
                expected_type = annotations[name]
                check_type(value, expected_type)

        result = func(*args, **kwargs)
        if 'return' in annotations:
            expected_return = annotations['return']
            check_type(result, expected_return)

        return result

    return wrapper
"""

# -----------------------------
# Typy Compiler
# -----------------------------
def compile_typy(file_path, output_path, enforce=False) -> None:
    with open(file_path, "r") as f:
        lines = f.readlines()

    py_lines = []

    # prepend enforcement machinery if compiling with enforce
    if enforce:
        with open("typy_enforce_lib.py", "w") as f:
            f.write(enforce_text)
        py_lines.append("from typy_enforce_lib import *")

    for i, line in enumerate(lines):
        print(f"[{i+1}/{len(lines)}] ", end="")
        indent = len(line) - len(line.lstrip())
        line = line.rstrip()
        if not line:
            py_lines.append(indent * " " + line)
            print("\x1b[38;2;255;0;0mempty line\x1b[0m")
            continue

        if line.startswith("#"):
            py_lines.append(indent * " " + line)
            print("\x1b[38;2;0;255;0mcommented line\x1b[0m")
            continue

        # Function: <type> <func>(<args>):
        func_match = re.match(r"(.+?)\s+(\w+)\((.*)\):", line)
        if func_match and line.strip().startswith(tuple(_type.__name__ for _type in assignable_types)):
            ret_type, name, args_str = func_match.groups()
            ret_type = ret_type.strip()

            # Convert types(...) → (int, str) form for Python
            if ret_type.startswith("types(") and ret_type.endswith(")"):
                ret_type = "(" + ret_type[len("types("):-1].strip() + ")"

            args = []
            args_annotations = []
            for arg in args_str.split(","):
                arg = arg.strip()
                if not arg:
                    continue

                arg_match = re.match(r"(.+?)\s+(\w+)(?:\s*=\s*(.+))?", arg)
                if not arg_match:
                    continue

                arg_type, arg_name, arg_val = arg_match.groups()
                arg_type = arg_type.strip()

                # Convert types(...) → tuple for args too
                if arg_type.startswith("types(") and arg_type.endswith(")"):
                    arg_type = "(" + arg_type[len("types("):-1].strip() + ")"

                arg_build_buffer = [f"{arg_name}"]

                if arg_type:
                    arg_build_buffer.append(f": {arg_type}")

                if arg_val:
                    arg_build_buffer.append(f" = {arg_val}")

                args.append("".join(arg_build_buffer))

                args_annotations.append(f"{arg_name}: {arg_type}")

            args_code = ", ".join(args)
            py_lines.append(indent * " " + f"def {name}({args_code}) -> {ret_type}:")
            if enforce:
                py_lines.append(py_lines[-1])
                py_lines[-2] = indent * " " + f"@enforce_wrapper"
            print(f"compiled \x1b[38;2;255;0;0m{line.strip()}\x1b[0m to \x1b[38;2;0;255;0m{"; ".join(py_lines[-1].splitlines())}\x1b[0m\n")
            continue

        # Variable: <type> <var> = <value>
        var_match = re.match(r"([\w\[\],\(\) ]+)\s+(\w+)\s*=\s*(.+)", line)
        if var_match and line.strip().startswith(tuple(_type.__name__ for _type in assignable_types)):
            typ, var, val = var_match.groups()
            py_lines.append(indent * " " + f"{var}: {typ.strip()} = {val.strip()}" + f"; check_type({var}, {typ.strip()})" * enforce)
            print(f"compiled \x1b[38;2;255;0;0m{line.strip()}\x1b[0m to \x1b[38;2;0;255;0m{py_lines[-1].strip()}\x1b[0m")
            continue

        print(f"kept line: \x1b[38;2;0;255;0m{line.strip()}\x1b[0m")
        py_lines.append(line)

    print("\nPushing Lines...")
    with open(output_path, "w") as f:
        for i, line in enumerate(py_lines, start=1):
            print(f"{i}/{len(py_lines)} ({i/len(py_lines)*100:.2f}%)\r")
            f.write(f"{line}\n")


print("DEBUG argv:", sys.argv)

# CLI arguments
if len(sys.argv) < 2:
    print("Usage: python compiler.py <file.typy> [--no-run]")
    print(sys.argv)
    sys.exit(1)

input_file = sys.argv[1]
run_file = "--run" in sys.argv
enforce = "--enforce" in sys.argv
debug = "--no-debug" not in sys.argv

output_file = os.path.splitext(input_file)[0] + ".py"

# -----------------------------
# Example usage
# -----------------------------
if __name__ == "__main__":
    turbo = True
    compile_typy(input_file, output_file, enforce=enforce)
    if run_file:
        subprocess.run([sys.executable, output_file])
