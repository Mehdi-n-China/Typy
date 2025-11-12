import os
import sys
import subprocess
from pathlib import Path
import re

class customs:
    types = ("types", "void", "None", "Literal", "Final", "Annotated", "Callable")

assignable_types = customs.types + tuple(
    _type.__name__
    for _type in [
        int, float, complex, bool, str, list, tuple, set,
        frozenset, dict, bytes, bytearray, object, memoryview
    ]
)

# text used in enforcement
enforce_text = """
from functools import wraps
import inspect
from typing import get_origin, get_args, Literal, Final, Annotated, Callable

def type_str(value) -> str:
    # check if its a type, then it probably can handle .__name__
    try:
        if isinstance(value, type):
            t = value
        else:
            t = type(value)
    
    # it my raise when trying to get its type
    except Exception:
        t = value

    # List
    if isinstance(value, list) and value:
        inner = type_str(value[0])
        return f"list[{inner}]"

    # Dict
    if isinstance(value, dict) and value:
        k, v = next(iter(value.items()))
        return f"dict[{type_str(k)}, {type_str(v)}]"

    # Set
    if isinstance(value, set) and value:
        inner = type_str(next(iter(value)))
        return f"set[{inner}]"

    # Tuple
    if isinstance(value, tuple) and value:
        # if it has more than 1 type, and all of them are the same
        if  len(value) > 1 and all(isinstance(x, type(value[0])) for x in value[1:]):
            return f"tuple[{type_str(value[0])}, ...]"
        
        # else just join them normally
        else:
            inner = ", ".join(type_str(v) for v in value)
            return f"tuple[{inner}]"
    
    # if it's a built-in, return name
    if t in [
            int, float, complex, bool, str, list, tuple, set, type(None),
            frozenset, dict, bytes, bytearray, object, memoryview
            ]:
        return t.__name__

    # return the name of the type + () to signify it's a custom type
    return t.__name__ + "()"

def check_type(value, expected, strict):
    # private function to return a boolean if value is of expected type
    def _check_type(value, expected):
        # handle multiple types (<types>)
        if isinstance(expected, tuple):
            for t in expected:
                if _check_type(value, t) is True:
                    return True
            return False

        # handle None
        if expected is None or expected is type(None):
            return value is None
        
        # get annotation parts
        origin = get_origin(expected)
        args = get_args(expected)

        # List
        if origin is list:
            # if not a list
            if not isinstance(value, list):
                return False
                
            # if it has arguments, look at nested, else return True
            if args:
                return all(_check_type(v, args[0]) for v in value)
                
            return True

        # Dict
        if origin is dict:
            # if not a dict
            if not isinstance(value, dict):
                return False
                
            # if it has arguments, look at nested, else return True
            if args and len(args) == 2:
                return all(_check_type(k, args[0]) and _check_type(v, args[1]) for k, v in value.items())
                
            return True

        # Tuple
        if origin is tuple:
            # if not a tuple
            if not isinstance(value, tuple):
                return False
            
            # if it has arguments, look at nested, else return True
            if args:
                # variable length tuple (infinite)
                if len(args) == 2 and args[1] is Ellipsis:
                    return all(_check_type(v, args[0]) for v in value)
                
                # if the length is not correct
                if len(args) != len(value):
                    return False
                
                # check if all nested args are correct
                return all(_check_type(v, t) for v, t in zip(value, args))
            return True

        # Set / frozenset
        if origin in (set, frozenset):
            # if not a set or frozenset
            if not isinstance(value, origin):
                return False
            
            # if it has arguments, look at nested, else return True
            if args:
                return all(_check_type(v, args[0]) for v in value)
            return True
        
        # if its a Callable just check that it's callable
        if origin is Callable:
            return callable(value)
        
        # if it's a special annotation, just return 2 to continue looping in case it's nested
        if origin in (Literal, Final, Annotated):
            return 2

        # any other type is attempted to be checked this way
        return isinstance(value, expected)
    
    # fetch bad types
    check_result = _check_type(value, expected)
    
    # if strict mode, raise errors
    if strict:
        # if multiple types
        if not check_result and isinstance(expected, tuple):
            # filter out special annotations
            final_list_types = []
            for item in expected:
                if item.__name__ not in (_type.__name__ for _type in (Literal, Final, Annotated)):
                    final_list_types.append(type_str(item))
            final_types = tuple(final_list_types)
            
            # make some types prettier
            if len(final_types) == 1:
                raise TypeError(f"[FATAL] Expected -> {final_types[0]}\\n"
                     f"                   Got -> {type_str(value)}")

            raise TypeError(f"[FATAL] Expected any of {final_types}\\n"
                 f"                   Got -> {type_str(value)}")
        
        # if single type
        elif not check_result:
            raise TypeError(f"[FATAL] Expected -> {type_str(expected)}\\n"
                 f"                   Got -> {type_str(value)}")
    
    # if not strict mode, just warn
    else:
        # if multiple types
        if not check_result and isinstance(expected, tuple):
            # filter out special annotations
            final_list_types = []
            for item in expected:
                if item.__name__ not in (_type.__name__ for _type in (Literal, Final, Annotated)):
                    final_list_types.append(type_str(item))
            final_types = tuple(final_list_types)
            
            # make some types prettier
            if len(final_types) == 1:
                print(f"\\n[WARNING] Expected -> {final_types[0]}\\n"
                        f"          Got -> {type_str(value)}")

            print(f"\\n[WARNING] Expected any of {final_types}\\n"
                    f"          Got -> {type_str(value)}")
        
        # if single type
        elif not check_result:
            print(f"\\n[WARNING] Expected -> {type_str(expected)}\\n"
                    f"          Got -> {type_str(value)}")

def enforce_types(func=None, *, strict) -> object:
    def decorator(func) -> object:
        # fetch the signature
        sig = inspect.signature(func)
        annotations = func.__annotations__
    
        @wraps(func)
        def wrapper(*args, **kwargs) -> object:
            # get defaults
            bound = sig.bind_partial(*args, **kwargs)
            bound.apply_defaults()
            
            MUTABLE_TYPES = (list, dict, set, bytearray, memoryview)
            
            # accept None as a sub for mutable defaults
            for name, value in bound.arguments.items():
                if name in annotations:
                    expected_type = annotations[name]
                    
                    # if we got a NoneType as argument
                    if value is None:
                        def origin_is_mutable(_type) -> bool:
                            t_origin = get_origin(_type) or _type
                            return t_origin in MUTABLE_TYPES
                        
                        # if it's a tuple, test if any inside are mutable
                        if isinstance(expected_type, tuple):
                            if any(origin_is_mutable(_type) for _type in expected_type):
                                continue
                        
                        # if it's a mutable itself
                        elif origin_is_mutable(expected_type):
                            continue
                    
                    # else check the type normally
                    check_type(value, expected_type, strict)
            
            # run func
            result = func(*args, **kwargs)
            
            # check annotations
            if 'return' in annotations:
                expected_return = annotations['return']
                check_type(result, expected_return, strict)
    
            return result
    
        return wrapper

    if func is None:
        return decorator
    return decorator(func)
"""

# ------- #
# Helpers #
# ------- #

def match_declaration(line: str, *, mode: str) -> re.Match | None:
    # check for function match
    if mode == "function":
        return re.match(
            r"(types\([\w\s,]+\)|[\w\s\[\],]+)" # Group 1: type
            r"\s+(\w+)\s*"                               # Group 2: function name
            r"\((.*)\)\s*:"                           # Group 3: parameters inside ()
            r"\s*(.*)",                               # Group 4: comment after colon
            line
        )

    # check for variable match
    elif mode == "variable":
        return re.match(
            r"(types\([\w\s,]+\)|[\w\[\],\(\). ]+)" # Group 1: type
            r"\s+([\w.]+)"                                 # Group 2: var name
            r"\s*="                                        # Group 3: equal sign
            r"\s*(.+)",                                    # Group 4: value and possible comments
            line
        )

    # check for argument match
    elif mode == "argument":
        return re.match(
            r"(types\([\w\s,]+\)|[\w\[\],\(\). ]+)"  # Group 1: type
            r"\s+([\w.]+)"                                  # Group 2: argument name
            r"(?:\s*=\s*(.+))?",                            # Group 3: optional default
            line
        )

    raise ValueError(f"Unknown mode {mode}")

def get_function_parts(matched_str: re.Match) -> list:
    item_list = []
    # add stripped items into a list for separation
    for item in matched_str.groups():
        if item is not None:
            item = item.strip()
            # handle void declarations
            if item == "void":
                item = "None"
            item_list.append(item.strip())

    # make sure the list is long enough in case comments break it
    if len(item_list) < 4:
        item_list.append(None)

    return item_list

def parse_args(args_str: str, *, debug_all: bool, debug_indent: str) -> str:
    args_list = split_args(args_str)

    args = []
    for i, arg in enumerate(args_list, start=1):
        arg = arg.strip()

        # deal with weird trailing commas and other bad spaces
        if not arg:
            continue

        # treat self or cls as special
        if arg in ("self", "cls"):
            if debug_all:
                # check if last arg
                if i == len(args_list):
                    print(debug_indent + f"   └─ [SPECIAL ARG] -> {arg}")
                else:
                    print(debug_indent + f"   │─ [SPECIAL ARG] -> {arg}")

            args.append(arg)
            continue

        if debug_all:
            if i == len(args_list):
                print(debug_indent + f"   └─ [NEW ARG] -> {arg}")
            else:
                print(debug_indent + f"   │─ [NEW ARG] -> {arg}")

        # Argument: <type> <var> = <optional_value>
        arg_match = match_declaration(arg, mode="argument")

        # raise bad formating
        if not arg_match:
            raise ValueError(f"[FATAL] Argument '{arg}' not formated properly")

        arg_type, arg_name, arg_val = arg_match.groups()
        arg_type = arg_type.strip()

        # convert types(<types>>) → (<types>) form for Python
        if arg_type.startswith("types(") and arg_type.endswith(")"):
            # check if it has multiple types
            if "," in arg_type:
                arg_type = arg_type.removeprefix("types").strip()

            # in case a single type is declared, fallback to no ()
            # for example types(Logger) logger -> logger: Logger
            else:
                arg_type = arg_type.removeprefix("types(").removesuffix(")").strip()

        # build and append the current arg
        args.append(f"{arg_name}: {arg_type if arg_type != "void" else "None"}" + f" = {arg_val}" * bool(arg_val))

        if debug_all:
            if i == len(args_list):
                print(debug_indent + f"      │─ [TYPE] -> {arg_type}")
                print(debug_indent + f"      │─ [NAME] -> {arg_name}")
                print(debug_indent + f"      └─ [DEFAULT] -> {arg_val if arg_val is not None and arg_val != "" else "No Default"}")
            else:
                print(debug_indent + f"   │  │─ [TYPE] -> {arg_type}")
                print(debug_indent + f"   │  │─ [NAME] -> {arg_name}")
                print(debug_indent + f"   │  └─ [DEFAULT] -> {arg_val if arg_val is not None and arg_val != "" else "No Default"}")

    return ", ".join(args)

def split_args(args_str: str) -> list[str]:
    args_list = []
    buffer = []
    depth = 0

    for char in args_str:
        # catch depth change
        if char == '(' or char == '[':
            depth += 1
        elif char == ')' or char == ']':
            depth -= 1

        # if top level and is a comma, catch as next arg
        elif char == ',' and depth == 0:
            args_list.append("".join(buffer).strip())
            buffer = []
            continue

        # append to buffer if not top level comma
        buffer.append(char)

    # flush buffer to include last argument
    if buffer:
        args_list.append("".join(buffer).strip())

    # make sure we are at depth 0
    if depth > 0:
        raise ValueError(f"[FATAL] -> Unbalanced parenthesis and brackets in {args_str}")
    return args_list

# ------------- #
# Typy Compiler #
# ------------- #

def compile_file(input_path, output_path, enforce, strict) -> None:
    with open(input_path, "r") as f:
        lines = f.readlines()

    print(f"[NEW FILE] -> {input_path}")

    py_lines = []

    is_protected = 0
    for i, line in enumerate(lines, start=1):
        # print line info
        print(f"[{i}/{len(lines)}] ", end="")

        # get a standard debug indentation
        debug_indent = " " * (len(f"{i}{len(lines)}") + 4)

        # transform tabs into spaces
        line_expanded = line.expandtabs(4)

        # get the indentation of the line of code
        indent = len(line_expanded) - len(line_expanded.lstrip())

        # normalize the line
        line = line.strip()

        # if empty line just ignore it
        if not line:
            py_lines.append(line)
            if debug: print("[EMPTY]")
            else: print("Done")
            continue

        # skip protected files
        if line == "typy:protect-file":
            if debug:
                print(f"[PROTECTION] -> Skipping File")
                for appended in py_lines:
                    print(appended)
                    if appended.strip():
                        print(debug_indent + f"[WARNING] -> File Protection should be declared as your first line")
            else: print(f"Skipping File")
            return


        # start protecting (until stopped)
        if line == "typy:protect-start":
            # make sure it's not protected
            if is_protected:
                raise PermissionError(f"[FATAL] Attempted to protect protected line")

            # make it infinite
            is_protected = -1

            if debug: print(f"[PROTECTION] -> Started Block")
            else: print(f"Done")
            continue

        # stop protecting
        elif line == "typy:protect-end":
            # remove protection
            is_protected = 0
            if debug: print(f"[PROTECTION] -> Ended Block")
            else: print(f"Done")
            continue

        # skip compilation on next line
        elif line == "typy:skip":
            # make sure it's not protected
            if is_protected:
                raise PermissionError(f"[FATAL] Attempted to skip protected line")
            if debug: print(f"[PROTECTION] -> Skipping Next Line")
            else: print(f"Done")

            # make it one line
            is_protected = 1
            continue

        # protect N number of lines from compilation
        elif line.startswith("typy:protect-for-"):
            if is_protected:
                raise PermissionError(f"[FATAL] Attempted to protect protected line")
            try:
                protection_duration = int(line.removeprefix("typy:protect-for-"))
                if protection_duration < 1:
                    raise TypeError
            except TypeError:
                raise TypeError(f"[FATAL] Invalid Line '{line}'")

            if debug:
                if protection_duration == 1:
                    print("[WARNING] -> Using 'typy:protect-for-' on a single line is okay, but prefer 'typy:skip'")
                else: print(f"[PROTECTION] -> For {protection_duration} Lines")
            else: print("Done")

            is_protected = protection_duration
            continue

        # check if line is protected
        if is_protected:
            is_protected -= 1
            if debug: print(f"[PROTECTED] -> {line}")
            else: print("Done")
            py_lines.append(line_expanded)
            continue

        # check if the line is a comment
        if line.startswith("#"):
            py_lines.append(" " * indent + line)
            if debug: print(f"[COMMENT] -> {line}")
            else: print("Done")
            continue

        # -------------------------------- #
        # Function: <type> <func>(<args>): #
        # -------------------------------- #
        func_match = match_declaration(line, mode="function")

        # if caught as a function, handle it
        if func_match:
            if debug_all: print(f"[NEW FUNCTION] -> {line}")

            # check it's a valid type or multi type declaration
            if line.startswith(assignable_types):
                # unpack values
                ret_type, name, args_str, comment = get_function_parts(func_match)

                if debug_all:
                    print(debug_indent + f"│─ [RETURNS] -> {ret_type}")
                    print(debug_indent + f"│─ [NAME] -> {name}")
                    print(debug_indent + f"│─ [COMMENT] -> {comment if comment is not None and comment != "" else 'No Comment'}")
                    print(debug_indent + f"└─ [RAW ARGS] -> {args_str if args_str is not None and args_str != "" else 'No Arguments'}")

                # convert types(<types>>) → (<types>) form for Python
                if ret_type.startswith("types(") and ret_type.endswith(")"):
                    # check if it has multiple types
                    if "," in ret_type:
                        ret_type = ret_type.removeprefix("types").strip()

                    # in case a single type is declared, fallback to no ()
                    # for example types(SomeClass) func(): -> def func() -> SomeClass:
                    else:
                        ret_type = ret_type.removeprefix("types(").removesuffix(")").strip()

                # parse args
                args_code = parse_args(args_str, debug_all=debug_all, debug_indent=debug_indent)

                # add type enforcement if necessary
                if enforce:
                    py_lines.append(" " * indent + f"@enforce_types(strict={strict})")

                # build the function line
                py_lines.append(" " * indent + f"def {name}({args_code}) -> {ret_type}:" + f"{" " + comment if comment else ""}")

                if debug: print(debug_indent * debug_all + f"[COMPILED] -> def {name}({args_code}) -> {ret_type}:" + f"{" " + comment if comment else ""}")
                else: print("Done")
                continue

        # -------------------------------- #
        # Variable: <type> <var> = <value> #
        # -------------------------------- #
        var_match = match_declaration(line, mode="variable")

        # if caught as a variable, handle it
        if var_match:

            # check it's a valid type or multi type declaration
            if line.strip().startswith(assignable_types):
                if debug_all: print(f"[NEW VARIABLE] -> {line}")

                # unpack values
                typ, var, val = tuple(item.strip() for item in var_match.groups())

                # check if a comment was included, else set it to None
                val, comment = tuple(item.strip() for item in (val.split("#", 1) if "#" in val else (val, "None")))

                if debug_all:
                    print(debug_indent + f"│─ [TYPE] -> {typ}")
                    print(debug_indent + f"│─ [NAME] -> {var}")
                    print(debug_indent + f"│─ [VALUE] -> {val}")
                    print(debug_indent + f"└─ [COMMENT] -> {comment if comment != "None" and comment != "" else 'No Comment'}")

                # convert types(<types>>) → (<types>) form for Python
                if typ.startswith("types(") and typ.endswith(")"):
                    # check if it has multiple types
                    if "," in typ:
                        typ = typ.removeprefix("types").strip()

                    # in case a single type is declared, fallback to no ()
                    # for example types(SomeClass) var = SomeClass() -> var: SomeClass = SomeClass():
                    else:
                        typ = typ.removeprefix("types(").removesuffix(")").strip()

                typ_str = (typ if typ != "void" else "None").strip()

                py_lines.append(" " * indent + f"{var}: {typ_str} = {val.strip()}" + f"; check_type({var}, {typ_str}, {strict})" * enforce + f"{" #" + comment if comment != "None" else ""}")
                if debug: print(debug_indent * debug_all + f"[COMPILED] -> {var}: {typ_str} = {val.strip()}" + f"; check_type({var}, {typ_str}, {strict})" * enforce + f"{" #" + comment if comment != "None" else ""}")
                else: print("Done")
                continue

        # if nothing was caught
        py_lines.append(" " * indent + line)
        if debug: print(f"[NO CHANGE] -> {line}")
        else: print("Done")

    # flush to output file
    print(f"\n[PUSHING TO FILE] -> {output_path}")

    # load file
    with open(output_path, "w") as f:
        # prepend enforcement machinery if compiling with enforce
        if enforce:
            f.write(enforce_text)
        for i, line in enumerate(py_lines, start=1):
            print(f"{i}/{len(py_lines)} ({i/len(py_lines)*100:.2f}%)\r", end="")
            f.write(f"{line}\n")
    print(f"[COMPILATION SUCCESSFUL]\n")

# --------- #
# Main Loop #
#---------- #

def start_compiler(input_path: str, output_path: str, enforce: bool, strict: bool):
    # build paths
    input_path = Path(input_path).resolve()
    output_path = Path(output_path).resolve()

    # if single file
    if input_path.is_file() and input_path.suffix == ".typy":
        # build file path
        out_file = input_path.with_suffix(".py").name

        # compile
        compile_file(input_path, out_file, enforce=enforce)

        # if asked to run
        if run_file:
            subprocess.run(["python", out_file])

    # if directory
    elif input_path.is_dir():
        # get all files
        files = list(input_path.rglob("*.typy"))
        total = len(files)

        # loop through files
        for idx, file in enumerate(files, 1):
            # build file path
            relative = file.relative_to(input_path)
            out_file = output_path / relative.with_suffix(".py")
            out_file.parent.mkdir(parents=True, exist_ok=True)

            # compile
            print(f"[FILE PROGRESS] -> {idx}/{total} ({idx/total*100:.2f}%)")
            compile_file(file, out_file, enforce, strict)

        # if asked to run and have an entry point
        if run_file and entry_point:
            subprocess.run(["python", entry_point])

    # if we can't build a valid path
    else:
        raise FileNotFoundError(f"[FATAL] {input_path} is not a .typy file or folder")


help_text = """
Usage: python typy.py <file.typy> [OPTIONS]

Positional Arguments:
    <file.typy>        Input file or folder to compile. Use 'root' to specify
                       the root directory explicitly.

Options:
    --run                Compile and immediately run the file.
    --run-here <entry>   Compile and run a specific entry point within the file.
                         Cannot be used with --run.
    
    --enforce            Enable type enforcement during compilation.
    --enforce-strict     Strict type enforcement. Automatically enables --enforce.
                         Cannot be used with --enforce.
    
    --no-debug           Disable debug output.
    --debug-all          Enable verbose debug output. Cannot be used with --no-debug.
                         
    --help               Show this help message and exit.

Examples:
    python compiler.py main.typy
        Compile 'main.typy' with default settings.
    
    python compiler.py main.typy --run
        Compile and run 'main.typy'.
    
    python compiler.py root --enforce
        Compile the current root folder with type enforcement.
    
    python compiler.py main.typy --run-here main_function
        Compile 'main.typy' and run 'main_function' as the entry point.
"""

if __name__ == "__main__":
    # CLI arguments
    if len(sys.argv) < 2:
        print(help_text)
        sys.exit(1)

    if "help" in sys.argv or "--help" in sys.argv:
        print(help_text)
        sys.exit(0)

    print(f"[STARTED COMPILER]")

    args = list(sys.argv[1:])

    # catch input file
    input_file = args[0]

    args.remove(input_file)

    # handle root case
    if input_file.endswith("root"):
        input_file = " "

    # assign output
    output_file = os.path.splitext(input_file)[0]

    # catch if the file is expected to be tun
    if "--run" in args:
        run_file = True
        args.remove("--run")
    else: run_file = False

    # catch target
    if "--run-here" in args:
        run_with_entry_point = True
    else: run_with_entry_point = False

    # catch specified entry point if any provided
    if run_with_entry_point:
        if run_file:
            raise ValueError("--run-here cannot be used with --run")
        else:
            run_file = True
            found_entry_point = False
            for i, arg in enumerate(args):
                if arg == "--run-here":
                    entry_point = args[i + 1]
                    args.remove("--run-here")
                    args.remove(entry_point)
                    found_entry_point = True
                    break
            if not found_entry_point:
                entry_point = None
    else: entry_point = None

    # catch enforce mode
    if "--enforce" in args:
        enforce = True
        args.remove("--enforce")
    else: enforce = False

    # catch strict mode
    if "--enforce-strict" in args:
        strict = True
        args.remove("--enforce-strict")
    else: strict = False

    # enforce arg safety
    if strict:
        if enforce:
            raise ValueError("--enforce--strict cannot be used with --enforce")
        else:
            enforce = True

    # catch skip debug
    if "--no-debug" in args:
        debug = False
        args.remove("--no-debug")
    else: debug = True

    # catch more debug
    if "--debug-all" in args:
        debug_all = True
        args.remove("--debug-all")
    else: debug_all = False

    # enforce arg safety
    if debug_all:
        if not debug:
            raise ValueError("--debug-all cannot be used with --no-debug")
        else:
            debug = True

    # catch unknown args
    if len(args) > 0:
        raise TypeError(f"[FATAL] Received unknown arguments: {args}")

    print(f"│─ [INPUT] -> {input_file if input_file != " " else "root"}")
    print(f"│─ [OUTPUT] -> {output_file if output_file != " " else "root"}")
    print(f"│─ [WILL RUN] -> {run_file}")
    print(f"│─ [ENTRY POINT] -> {entry_point if run_file else "N/A"}")
    print(f"│─ [ENFORCE] -> {enforce}")
    print(f"│─ [STRICT] -> {strict}")
    print(f"└─ [DEBUG LEVEL] -> {debug_all + debug}")
    print()

    # start main loop
    start_compiler(input_file, output_file, enforce, strict)
