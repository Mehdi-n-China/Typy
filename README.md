# Typy

**Typy is a lightweight, statically-typed extension of Python that introduces simple, intuitive syntax for enforcing variable and function types without breaking Python’s natural flexibility.**

    ⚠️ This project is not related to the existing typy module on PyPI.
    It’s a completely separate implementation that does not affect or modify any external libraries or the Python interpreter itself.

## 💡 Overview

Typy code uses nearly identical syntax to Python — the only differences are in variable and function declarations:

# Typy syntax
    int x = 5
    str name = "Mehdi"
    
    int add(int a = 1, int b = 2):
        return a + b
    
When compiled, Typy translates directly to standard Python code with optional runtime type enforcement depending on your chosen mode.

⚙️ Features

Full compatibility with all existing Python libraries and syntax.

Compile-time and runtime type enforcement for both variables and functions.

Optional multi-type return annotations using types(<types>).

Two operating modes — enforce and normal.

Unsafe mode to bypass type checks when needed.

Designed for conscious type use, not type restriction — you can still use Python’s dynamic behavior, just explicitly.

### 🔗 Nested Types

Typy supports **nested type definitions** just like Python’s type hints, such as:

list[str] names = ["Mehdi", "Ajana", "Jiakai"]
dict[str, int] ages = {"Mehdi": 19, "Ajana": 20}

🚀 Modes
🧩 Enforce Mode

Used during development.
All variable assignments, inputs, and return values are checked to match declared types.
Perfect for catching type errors and debugging early.

⚡ Normal Mode

Used for final builds.
Compiles your code to plain Python and strips all type enforcement for maximum performance.
This removes all runtime overhead while preserving your logic.

🔓 Unsafe Mode

If you want to skip type checking in specific parts of your code, you can just write standard Python syntax:

def foo(a, b):
    return a + b

Unsafe mode simply ignores Typy’s type enforcement for those definitions — ideal for rapid prototyping or low-impact functions.

🧠 Examples

# Normal typed code
float radius = 5.2

float area(float r = radius):
    return 3.1415 * r * r

print(area())

# Multiple return types
types(int, str) format_id(int id = 5):
    if id == 5:
        return "Admin"
    return id

You can use multiple return types to allow for flexible return patterns without abandoning static safety.

🛠 Compilation

Typy code (.typy files) is compiled into pure Python (.py) with optional type enforcement.
This means it runs everywhere Python runs — no runtime dependencies, no external module injection.

🧾 Philosophy

Typy doesn’t try to cage Python’s dynamic nature.
It’s built to make you think consciously about your type decisions — not to block creativity.
It lets you enjoy the fluidity of Python while catching the dumb type mistakes before they fuck your runtime.

🔧 Example Compilation Flow

typy compile example.typy --mode enforce
typy compile example.typy --mode normal

enforce mode → used in dev, full type safety.

normal mode → production build, optimized output.
