# Typy

**Typy is a lightweight, statically-typed extension of Python that introduces simple, intuitive syntax for enforcing variable and function types without breaking Python’s natural flexibility.**
    
⚠️ This project is **NOT** related to the existing typy module on PyPI.
It’s a completely separate implementation that does not affect or modify any external libraries or the Python interpreter itself.
    
# 💡 Overview

Typy code uses nearly identical syntax to Python — the only differences are in **variable and function declarations**:

# Typy syntax

    str greeting = "hello world"
    
    int add(int a = 1, int b = 2):
        return a + b

When compiled, Typy translates directly to standard Python code with **optional runtime type enforcement** depending on your chosen mode.

# ⚙️ Features

**Full** compatibility with **all existing Python libraries and syntax**.

Compile-time and runtime **type enforcement** for both **variables and functions**.

Optional **multi-type** return annotations using **types(<types>)**.

```python
    # input.typy
    types(int, float) get_modulo(types(int, float) number = 0, types(int, float) modulo = 1):
        return number % modulo

    # output.py
    def get_modulo(number: (int, float) = 0, modulo: (int, float) = 1) -> (int, float):
        return number % modulo
```
    
Two operating modes — **enforce and normal**.

**Unsafe mode** to **bypass type checks** when needed.

Designed for **conscious type use, not type restriction** — you can still use Python’s **dynamic behavior**, just **explicitly**.

# 🔗 Nested Types

Typy supports **nested type definitions** just like Python’s type hints, such as:

```python
list[str] listified_greeting = ["hello", "world"]
dict[str, int] ages = {"Bob": 18, "Alice": 19}
```

# 🚀 Modes

## 🧩 Enforce Mode → used in dev, full type safety

Used **during development**.

**All** variable assignments, inputs, and return values are **checked to match declared types**.

Perfect for **catching type errors and debugging early**.

## ⚡ Normal Mode → production build, optimized output

Used for **final builds**.

Compiles your code to plain Python and **strips all type enforcement** for **maximum performance**.

This removes all runtime overhead while preserving your logic.

#### Note: Do not use this during developement. It's meant to ship only.

🔓 Unsafe Mode

If you want to **skip type checking** in specific parts of your code, you can **just write standard Python syntax**:

    def foo(a, b):
        return a + b

Unsafe mode simply **ignores Typy’s type enforcement** for those definitions — **only use if you explicitely want to skip type checking** for a specific reason. **Otherwise, use types(<types>)**.

# 🧠 Examples

## Normal typed code

    float radius = 5.2
    
    float area(float r = radius):
        return 3.1415 * (r ** 2)
    
    print(area())

## Multiple return types

    types(int, str) format_id(int id = 5):
        if id == 5:
            return "Admin"
        return id

You can use **multiple return types** to **allow for flexible return patterns without abandoning static safety**.

# 🛠 Compilation

Typy code (**.typy**) is compiled into pure Python (**.py**) with **optional type enforcement**.

This means it **runs everywhere Python runs** — no runtime dependencies, no external module injection.

# 🧾 Philosophy

**Typy doesn’t try to cage Python’s dynamic nature**.

It’s built to **make you think consciously about your type decisions — not to block creativity**.

It lets you **enjoy the fluidity of Python while catching the dumb type mistakes** before they break your runtime.

# 🔧 Example Compilation Flow
    
    typy compile example.typy --mode enforce
    python typy compile example.typy --mode normal
