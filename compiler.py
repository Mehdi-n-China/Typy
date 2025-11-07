import os
import sys
import subprocess

# Assignable types
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

print("DEBUG argv:", sys.argv)

# CLI arguments
if len(sys.argv) < 2:
    print("Usage: python compiler.py <file.typy> [--no-run]")
    print(sys.argv)
    sys.exit(1)


input_file = sys.argv[1]
run_file = "--no-run" not in sys.argv

debug = True

output_file = os.path.splitext(input_file)[0] + ".py"

with open(input_file, "r") as f, open(output_file, "w") as dest:
    for line in f:
        # Detect indentation
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()

        if not stripped:
            dest.write("\n")
            continue

        matched_type = False
        for _type in assignable_types:
            if stripped.startswith(_type.__name__ + " "):
                parts = stripped.split()
                var_name = parts[1]
                rest = " ".join(parts[2:])
                dest.write(" " * indent + f"{var_name}: {_type.__name__} {rest}\n")
                matched_type = True
                if debug: print(f"compiled {stripped} to {f"{var_name}: {_type.__name__} {rest}"}")
                break

        if matched_type:
            continue

        if stripped.startswith("func."):
            parts = stripped.split()
            return_type = parts[0][5:]
            func_def = " ".join(parts[1:])[:-1]
            dest.write(" " * indent + f"def {func_def} -> {return_type}:\n")
            matched_type = True

        if matched_type:
            continue

        # Keep original line with indentation
        dest.write(" " * indent + stripped + "\n")

print(f"Transpiled '{input_file}' → '{output_file}'")

if run_file:
    subprocess.run([sys.executable, output_file])
