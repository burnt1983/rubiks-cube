#!/usr/bin/env python3
"""Open the 3D Rubik's cube in a borderless transparent window."""

from __future__ import annotations

import json
import os
import signal
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HTML = ROOT / "index.html"
PID = Path.home() / ".cache" / "rubik-cube.pid"
CFG = Path.home() / ".config" / "rubik-cube" / "window.json"
WIDTH, HEIGHT = 760, 840
THREE_FILES = ("three.module.js", "three.core.js")


def ensure_three() -> None:
    """Unpack the vendored Three.js files next to this script."""
    import base64
    import gzip

    vendor = ROOT / "vendor"
    for name in THREE_FILES:
        dest = ROOT / name
        if dest.is_file() and dest.stat().st_size > 10000:
            continue
        pieces = sorted(vendor.glob(f"{name}.gz.b64*"))
        if not pieces:
            raise SystemExit(f"rubik-cube: missing packed {name}")
        packed = "".join(piece.read_text(encoding="ascii") for piece in pieces)
        dest.write_bytes(gzip.decompress(base64.b64decode(packed)))


def prefer_xwayland(max_wait_s: float = 25.0) -> str:
    """Use XWayland so the window can reopen on the same pixels. Call first."""
    if os.environ.get("DESKLET_NATIVE_WAYLAND"):
        os.environ["GDK_BACKEND"] = "wayland"
        return "wayland"
    forced = os.environ.get("GDK_BACKEND")
    if forced and forced != "x11":
        return forced
    display = os.environ.get("DISPLAY") or ":0"
    os.environ["DISPLAY"] = display
    screen = display.split(":")[-1].split(".")[0]
    if not screen.isdigit():
        screen = "0"
    sock = f"/tmp/.X11-unix/X{screen}"
    deadline = time.time() + max_wait_s
    while not os.path.exists(sock):
        if time.time() >= deadline:
            sys.stderr.write(
                "rubik-cube: XWayland is not up; this window cannot restore its position\n"
            )
            return forced or "wayland"
        time.sleep(0.2)
    os.environ["GDK_BACKEND"] = "x11"
    return "x11"


if __name__ == "__main__" and "--unpack" in sys.argv:
    ensure_three()
    raise SystemExit(0)

prefer_xwayland()

# Keep the page clear. The dmabuf renderer paints an opaque backdrop.
os.environ.setdefault("WEBKIT_DISABLE_DMABUF_RENDERER", "1")

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
gi.require_version("WebKit2", "4.1")
from gi.repository import Gdk, GLib, Gtk, WebKit2
import cairo


def read_pid() -> int | None:
    try:
        pid = int(PID.read_text().strip())
    except (OSError, ValueError):
        return None
    if pid <= 0:
        return None
    try:
        os.kill(pid, 0)
    except OSError:
        return None
    return pid


def load_geo():
    try:
        data = json.loads(CFG.read_text())
        return int(data["x"]), int(data["y"]), int(data["w"]), int(data["h"])
    except (OSError, ValueError, KeyError, TypeError):
        return None


def main() -> None:
    ensure_three()
    other = read_pid()
    if other and other != os.getpid():
        os.kill(other, signal.SIGUSR1)
        return

    # Keep this different from the desktop-file id so clicking the icon
    # starts this script again instead of only focusing the open window.
    GLib.set_prgname("rubik-cube-window")
    Gdk.set_program_class("rubik-cube-window")

    window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
    window.set_title("Rubik's Cube")
    icon = Path.home() / ".local/share/icons/hicolor/256x256/apps/rubik-cube.png"
    if icon.is_file():
        window.set_icon_from_file(str(icon))
    else:
        window.set_icon_name("rubik-cube")
    window.set_decorated(False)
    window.set_app_paintable(True)
    window.set_resizable(True)
    geo = load_geo()
    if geo:
        window.set_default_size(max(520, geo[2]), max(560, geo[3]))
    else:
        window.set_default_size(WIDTH, HEIGHT)
    window.set_size_request(480, 520)

    screen = window.get_screen()
    visual = screen.get_rgba_visual() if screen is not None else None
    if visual is not None:
        window.set_visual(visual)

    web = WebKit2.WebView()
    rgba = Gdk.RGBA()
    rgba.red = rgba.green = rgba.blue = rgba.alpha = 0
    web.set_background_color(rgba)
    settings = web.get_settings()
    settings.set_enable_webgl(True)
    # The page is local. This only lets it import the Three.js files beside it.
    settings.set_allow_file_access_from_file_urls(True)
    try:
        settings.set_hardware_acceleration_policy(WebKit2.HardwareAccelerationPolicy.ALWAYS)
    except Exception:
        pass
    window.add(web)

    def paint_clear(_widget, context):
        context.set_operator(cairo.OPERATOR_SOURCE)
        context.set_source_rgba(0, 0, 0, 0)
        context.paint()
        context.set_operator(cairo.OPERATOR_OVER)
        return False

    window.connect("draw", paint_clear)

    def on_message(_manager, value):
        try:
            if hasattr(value, "get_js_value"):
                value = value.get_js_value()
            text = value.to_string()
        except Exception:
            text = str(value)
        text = text.strip()
        if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
            text = text[1:-1]
        if text == "quit":
            window.destroy()
            return
        if text.startswith("move:"):
            parts = text[5:].split(",")
            if len(parts) != 2:
                return
            try:
                dx = int(round(float(parts[0])))
                dy = int(round(float(parts[1])))
            except ValueError:
                return
            scale = window.get_scale_factor() or 1
            x, y = window.get_position()
            window.move(x + dx * scale, y + dy * scale)
            return
        if text == "move-end":
            save_geo()

    manager = web.get_user_content_manager()
    manager.register_script_message_handler("rubik")
    manager.connect("script-message-received::rubik", on_message)
    web.connect("context-menu", lambda *_args: True)

    # A held left-button drag moves the window. A click without movement
    # stays put, so that click can turn the cube instead.
    web.add_events(
        Gdk.EventMask.BUTTON_PRESS_MASK
        | Gdk.EventMask.BUTTON_RELEASE_MASK
        | Gdk.EventMask.POINTER_MOTION_MASK
    )
    drag_state = {"armed": False, "on": False, "x": 0.0, "y": 0.0, "ox": 0.0, "oy": 0.0}

    def on_press(_widget, event):
        if event.button != 1:
            return False
        drag_state["armed"] = True
        drag_state["on"] = False
        drag_state["ox"] = drag_state["x"] = float(event.x_root)
        drag_state["oy"] = drag_state["y"] = float(event.y_root)
        return False

    def on_motion(_widget, event):
        if not drag_state["armed"]:
            return False
        if not drag_state["on"]:
            if abs(event.x_root - drag_state["ox"]) < 6 and abs(event.y_root - drag_state["oy"]) < 6:
                return False
            drag_state["on"] = True
            drag_state["x"] = float(event.x_root)
            drag_state["y"] = float(event.y_root)
        dx = event.x_root - drag_state["x"]
        dy = event.y_root - drag_state["y"]
        drag_state["x"] = float(event.x_root)
        drag_state["y"] = float(event.y_root)
        if dx or dy:
            x, y = window.get_position()
            window.move(int(round(x + dx)), int(round(y + dy)))
        return False

    def on_release(_widget, event):
        if event.button == 1:
            moved = drag_state["on"]
            drag_state["armed"] = False
            drag_state["on"] = False
            if moved:
                save_geo()
        return False

    web.connect("button-press-event", on_press)
    web.connect("motion-notify-event", on_motion)
    web.connect("button-release-event", on_release)

    placed = {"done": False}

    def place(*_args):
        if placed["done"]:
            return False
        placed["done"] = True
        if geo:
            window.move(geo[0], geo[1])
            return False
        display = window.get_display()
        monitor = None
        if display is not None:
            monitor = display.get_primary_monitor() or (
                display.get_monitor(0) if display.get_n_monitors() else None
            )
        if monitor is None:
            return False
        work = monitor.get_workarea()
        w, h = window.get_size()
        window.move(work.x + max(0, (work.width - w) // 2), work.y + max(0, (work.height - h) // 2))
        return False

    def save_geo():
        x, y = window.get_position()
        w, h = window.get_size()
        # A shutdown used to write 0,32. Skip that.
        if w < 100 or h < 100:
            return
        CFG.parent.mkdir(parents=True, exist_ok=True)
        CFG.write_text(json.dumps({"x": int(x), "y": int(y), "w": int(w), "h": int(h)}))

    save_id = {"id": None}

    def schedule_save(*_args):
        if save_id["id"] is not None:
            GLib.source_remove(save_id["id"])
        save_id["id"] = GLib.timeout_add(400, flush_save)
        return False

    def flush_save():
        save_id["id"] = None
        save_geo()
        return False

    def on_usr1(*_args):
        # A second launch, from clicking the icon again, closes the cube.
        GLib.idle_add(window.destroy)

    signal.signal(signal.SIGUSR1, on_usr1)
    signal.signal(signal.SIGTERM, lambda *_a: window.destroy())

    def cleanup(*_args):
        if save_id["id"] is not None:
            GLib.source_remove(save_id["id"])
            save_id["id"] = None
        try:
            if PID.exists() and int(PID.read_text().strip()) == os.getpid():
                PID.unlink()
        except (OSError, ValueError):
            pass
        Gtk.main_quit()

    PID.parent.mkdir(parents=True, exist_ok=True)
    PID.write_text(str(os.getpid()))

    window.connect("realize", place)
    window.connect("configure-event", schedule_save)
    window.connect("destroy", cleanup)
    window.connect("key-press-event", lambda _w, event: window.destroy() if event.keyval == Gdk.KEY_Escape else None)

    try:
        web.get_context().clear_cache()
    except Exception:
        pass
    # Read the page from disk each launch so a stale WebKit cache cannot
    # keep an older cube on screen.
    web.load_html(HTML.read_text(encoding="utf-8"), HTML.as_uri())
    window.show_all()
    web.grab_focus()
    Gtk.main()


if __name__ == "__main__":
    main()
