from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image


class CaptureUnavailable(RuntimeError):
    pass


class WindowSelectionError(RuntimeError):
    pass


@dataclass(frozen=True)
class WindowIdentity:
    window_id: int
    title: str
    instance: str
    window_class: str


def parse_wm_class(value: str) -> tuple[str, str]:
    match = re.fullmatch(r'WM_CLASS\(STRING\) = "([^"\r\n]*)", "([^"\r\n]*)"\s*', value)
    if match is None:
        raise WindowSelectionError("invalid WM_CLASS response")
    return match.group(1), match.group(2)


def select_exact_window(
    windows: tuple[WindowIdentity, ...], *, title: str, instance: str, window_class: str
) -> WindowIdentity:
    matches = tuple(item for item in windows if item.title == title and item.instance == instance
                    and item.window_class == window_class)
    if not matches:
        raise WindowSelectionError("selected window is not available")
    if len(matches) != 1:
        raise WindowSelectionError("selected window identity is ambiguous")
    return matches[0]


class XWindowCapture:
    """Exact-identity XWayland capture with ephemeral raw storage."""

    def __init__(self) -> None:
        for executable in ("xdotool", "xprop", "import"):
            if shutil.which(executable) is None:
                raise CaptureUnavailable(f"{executable} executable is not installed")

    def list_windows(self) -> tuple[WindowIdentity, ...]:
        search = self._run(["xdotool", "search", "--name", ".*"])
        windows: list[WindowIdentity] = []
        for raw_id in search.stdout.splitlines():
            try:
                window_id = int(raw_id.strip())
                windows.append(self.inspect(window_id))
            except (ValueError, WindowSelectionError):
                continue
        return tuple(windows)

    def inspect(self, window_id: int) -> WindowIdentity:
        if window_id <= 0:
            raise WindowSelectionError("window id must be positive")
        title = self._run(["xdotool", "getwindowname", str(window_id)]).stdout.rstrip("\n")
        response = self._run(["xprop", "-id", str(window_id), "WM_CLASS"]).stdout
        instance, window_class = parse_wm_class(response)
        return WindowIdentity(window_id, title, instance, window_class)

    def capture(self, identity: WindowIdentity) -> Image.Image:
        before = self.inspect(identity.window_id)
        if before != identity:
            raise WindowSelectionError("window identity changed before capture")
        with tempfile.TemporaryDirectory(prefix="zenith-vision-capture-") as directory:
            path = Path(directory) / "raw.png"
            self._run(["import", "-window", str(identity.window_id), str(path)], timeout=15.0)
            after = self.inspect(identity.window_id)
            if after != identity:
                raise WindowSelectionError("window identity changed during capture")
            with Image.open(path) as source:
                return source.convert("RGB").copy()

    @staticmethod
    def _run(args: list[str], timeout: float = 5.0) -> subprocess.CompletedProcess[str]:
        try:
            result = subprocess.run(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, text=True, timeout=timeout, check=False)
        except subprocess.TimeoutExpired as error:
            raise CaptureUnavailable(f"{args[0]} timed out") from error
        if result.returncode != 0:
            raise WindowSelectionError(f"{args[0]} failed with status {result.returncode}")
        return result
