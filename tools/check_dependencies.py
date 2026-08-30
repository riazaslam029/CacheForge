#!/usr/bin/env python3
"""
Zero-Dependency Auditor Tool for CacheForge.
Parses AST of all Python source files to ensure ZERO third-party runtime imports exist.
"""

import ast
import os
import sys
from typing import Set, List

# Standard library module list fallback if sys.stdlib_module_names not available (Python 3.10+)
STDLIB_MODULES = set(getattr(sys, "stdlib_module_names", {
    "abc", "argparse", "array", "ast", "asyncio", "base64", "bisect", "builtins",
    "bz2", "calendar", "cmath", "cmd", "code", "codecs", "collections", "colorsys",
    "compileall", "concurrent", "configparser", "contextlib", "contextvars", "copy",
    "copyreg", "cProfile", "csv", "ctypes", "curses", "dataclasses", "datetime",
    "dbm", "decimal", "difflib", "dis", "doctest", "email", "enum", "errno", "faulthandler",
    "fcntl", "filecmp", "fileinput", "fnmatch", "fractions", "ftplib", "functools",
    "gc", "getopt", "getpass", "gettext", "glob", "graphlib", "gzip", "hashlib",
    "heapq", "hmac", "html", "http", "imaplib", "imghdr", "importlib", "inspect",
    "io", "ipaddress", "itertools", "json", "keyword", "linecache", "locale",
    "logging", "lzma", "mailbox", "mailcap", "math", "mimetypes", "mmap", "modulefinder",
    "msilib", "msvcrt", "multiprocessing", "netrc", "nntplib", "numbers", "operator",
    "optparse", "os", "pathlib", "pdb", "pickle", "pickletools", "pkgutil", "platform",
    "plistlib", "poplib", "posix", "posixpath", "pprint", "profile", "pstats", "pty",
    "pwd", "py_compile", "pyclbr", "pydoc", "queue", "quopri", "random", "re",
    "readline", "resource", "rlcompleter", "runpy", "sched", "select", "selectors",
    "shelve", "shutil", "signal", "site", "smtpd", "smtplib", "sndhdr", "socket",
    "socketserver", "spwd", "sqlite3", "ssl", "stat", "statistics", "string",
    "stringprep", "struct", "subprocess", "sunau", "symtable", "sys", "sysconfig",
    "syslog", "tarfile", "telnetlib", "tempfile", "termios", "test", "textwrap",
    "threading", "time", "timeit", "tkinter", "token", "tokenize", "tomllib",
    "trace", "traceback", "tracemalloc", "tty", "types", "typing", "unicodedata",
    "unittest", "urllib", "uu", "uuid", "venv", "warnings", "wave", "weakref",
    "webbrowser", "winreg", "winsound", "wsgiref", "xdrlib", "xml", "xmlrpc",
    "zipapp", "zipfile", "zipimport", "zlib"
}))

LOCAL_PROJECT_MODULES = {"cacheforge", "tests", "tools"}


def extract_imports(filepath: str) -> Set[str]:
    """Extract top-level imported package names from a Python source file using AST."""
    imports = set()
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read(), filename=filepath)
        except SyntaxError as e:
            print(f"Syntax error while parsing {filepath}: {e}")
            return imports

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_pkg = alias.name.split(".")[0]
                imports.add(root_pkg)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root_pkg = node.module.split(".")[0]
                imports.add(root_pkg)
    return imports


def audit_repository(root_dir: str) -> bool:
    """Audit all python files in project directory for non-stdlib imports."""
    py_files: List[str] = []
    for dirpath, _, filenames in os.walk(root_dir):
        if "node_modules" in dirpath or ".git" in dirpath or "__pycache__" in dirpath:
            continue
        for f in filenames:
            if f.endswith(".py"):
                py_files.append(os.path.join(dirpath, f))

    disallowed_found = False
    print(f"Auditing {len(py_files)} Python files for zero third-party dependencies...")

    for filepath in sorted(py_files):
        rel_path = os.path.relpath(filepath, root_dir)
        file_imports = extract_imports(filepath)

        for pkg in file_imports:
            if pkg not in STDLIB_MODULES and pkg not in LOCAL_PROJECT_MODULES:
                print(f"❌ DISALLOWED DEPENDENCY DETECTED: File '{rel_path}' imports non-stdlib package '{pkg}'")
                disallowed_found = True

    if disallowed_found:
        print("\nDependency audit FAILED: Third-party dependencies found!")
        return False
    else:
        print("✓ Dependency audit PASSED: 100% zero third-party runtime dependencies!")
        return True


if __name__ == "__main__":
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    success = audit_repository(repo_root)
    sys.exit(0 if success else 1)
