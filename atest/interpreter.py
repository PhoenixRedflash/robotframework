import os
import re
import subprocess
import sys
from pathlib import Path


def get_variables(path, name=None, version=None):
    return {"INTERPRETER": Interpreter(path, name, version)}


class Interpreter:

    def __init__(self, path, name=None, version=None):
        self.path = path
        self.interpreter = self._get_interpreter(path)
        if not name:
            name, version = self._get_name_and_version()
        self.name = name
        self.version = version
        self.version_info = tuple(int(item) for item in version.split("."))
        self.src_dir = Path(__file__).parent.parent / "src"

    def _get_interpreter(self, path):
        path = path.replace("/", os.sep)
        return [path] if os.path.exists(path) else path.split()

    def _get_name_and_version(self):
        try:
            output = subprocess.check_output(
                self.interpreter + ["-V"],
                stderr=subprocess.STDOUT,
                encoding="UTF-8",
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as err:
            raise ValueError(f"Failed to get interpreter version: {err}")
        name, version = output.split()[:2]
        name = name if "PyPy" not in output else "PyPy"
        version = re.match(r"\d+\.\d+\.\d+", version).group()
        return name, version

    @property
    def os(self):
        for condition, name in [
            (self.is_linux, "Linux"),
            (self.is_osx, "OS X"),
            (self.is_windows, "Windows"),
        ]:
            if condition:
                return name
        return sys.platform

    @property
    def output_name(self):
        return f"{self.name}-{self.version}-{self.os}".replace(" ", "")

    @property
    def excludes(self):
        if self.is_pypy:
            yield "no-pypy"
            yield "require-lxml"
        for require in [(3, 9), (3, 10), (3, 14)]:
            if self.version_info < require:
                yield "require-py%d.%d" % require
        if self.is_windows:
            yield "no-windows"
        if not self.is_windows:
            yield "require-windows"
        if self.is_osx:
            yield "no-osx"
        if not self.is_linux:
            yield "require-linux"

    @property
    def is_python(self):
        return self.name == "Python"

    @property
    def is_pypy(self):
        return self.name == "PyPy"

    @property
    def is_linux(self):
        return "linux" in sys.platform

    @property
    def is_osx(self):
        return sys.platform == "darwin"

    @property
    def is_windows(self):
        return os.name == "nt"

    @property
    def runner(self):
        return self.interpreter + [str(self.src_dir / "robot/run.py")]

    @property
    def rebot(self):
        return self.interpreter + [str(self.src_dir / "robot/rebot.py")]

    @property
    def libdoc(self):
        return self.interpreter + [str(self.src_dir / "robot/libdoc.py")]

    @property
    def testdoc(self):
        return self.interpreter + [str(self.src_dir / "robot/testdoc.py")]

    @property
    def underline(self):
        return "-" * len(str(self))

    def __str__(self):
        return f"{self.name} {self.version} on {self.os}"
