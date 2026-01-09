import argparse
import colorsys
import ctypes
import threading
import time
import tkinter as tk
from dataclasses import dataclass
from ctypes import wintypes

import mss
from pynput import keyboard

INPUT_MOUSE = 0
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
try:
    ULONG_PTR = wintypes.ULONG_PTR
except AttributeError:
    ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("mi", MOUSEINPUT)]


def send_mouse(flags: int) -> bool:
    inp = INPUT(type=INPUT_MOUSE, mi=MOUSEINPUT(0, 0, 0, flags, 0, ULONG_PTR(0)))
    sent = ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))
    return sent == 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "检测屏幕中心区域的颜色，识别状态变化时触发鼠标中键，并在屏幕显示状态。"
        )
    )
    parser.add_argument("--sample-size", type=int, default=10, help="采样区域边长（像素）")
    parser.add_argument("--fps", type=float, default=100.0, help="检测频率（每秒次数）")
    parser.add_argument("--toggle-key", type=str, default="f8", help="启用/禁用检测的按键（例如 f8）")
    parser.add_argument("--test-key", type=str, default="f9", help="测试中键点击的按键（例如 f9）")
    parser.add_argument("--test-left-key", type=str, default="f10", help="测试左键点击的按键（例如 f10）")
    parser.add_argument("--hue-min", type=float, default=35.0, help="金色最小色相（度）")
    parser.add_argument("--hue-max", type=float, default=60.0, help="金色最大色相（度）")
    parser.add_argument("--sat-min", type=float, default=0.4, help="金色最小饱和度（0-1）")
    parser.add_argument("--val-min", type=float, default=0.4, help="金色最小亮度（0-1）")
    return parser.parse_args()


@dataclass
class State:
    enabled: bool = True
    detected: bool = False
    trigger_count: int = 0
    test_count: int = 0
    left_test_count: int = 0
    indicator_color: str = "green"


def is_gold_like(rgb: tuple[int, int, int], hue_min: float, hue_max: float, sat_min: float, val_min: float) -> bool:
    red, green, blue = rgb
    hue, saturation, value = colorsys.rgb_to_hsv(red / 255, green / 255, blue / 255)
    hue_deg = hue * 360.0
    return hue_min <= hue_deg <= hue_max and saturation >= sat_min and value >= val_min


def region_contains_gold(pixels: bytes, hue_min: float, hue_max: float, sat_min: float, val_min: float) -> bool:
    for i in range(0, len(pixels), 4):
        blue = pixels[i]
        green = pixels[i + 1]
        red = pixels[i + 2]
        if is_gold_like((red, green, blue), hue_min, hue_max, sat_min, val_min):
            return True
    return False


def click_middle() -> None:
    if send_mouse(MOUSEEVENTF_MIDDLEDOWN) and send_mouse(MOUSEEVENTF_MIDDLEUP):
        return
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_MIDDLEDOWN, 0, 0, 0, 0)
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_MIDDLEUP, 0, 0, 0, 0)


def click_left() -> None:
    if send_mouse(MOUSEEVENTF_LEFTDOWN) and send_mouse(MOUSEEVENTF_LEFTUP):
        return
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


def set_dpi_awareness() -> None:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass


def enable_click_through(root: tk.Tk, transparent_color: str) -> None:
    try:
        hwnd = root.winfo_id()
        ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
        ex_style |= 0x00080000 | 0x00000020
        ctypes.windll.user32.SetWindowLongW(hwnd, -20, ex_style)
        red16, green16, blue16 = root.winfo_rgb(transparent_color)
        red = red16 // 257
        green = green16 // 257
        blue = blue16 // 257
        color_key = (blue << 16) | (green << 8) | red
        ctypes.windll.user32.SetLayeredWindowAttributes(hwnd, color_key, 0, 0x1)
        root.wm_attributes("-transparentcolor", transparent_color)
    except OSError:
        pass
    except tk.TclError:
        pass


def build_overlay(sample_size: int, monitor: dict) -> tuple[tk.Tk, tk.Canvas, tk.Label, int]:
    root = tk.Tk()
    root.title("AutoDPI Overlay")
    root.attributes("-topmost", True)
    root.overrideredirect(True)
    transparent_color = "magenta"
    root.configure(bg=transparent_color)
    try:
        root.wm_attributes("-transparentcolor", transparent_color)
    except tk.TclError:
        pass
    screen_width = monitor["width"]
    screen_height = monitor["height"]
    screen_left = monitor.get("left", 0)
    screen_top = monitor.get("top", 0)
    root.geometry(f"{screen_width}x{screen_height}+{screen_left}+{screen_top}")
    root.update_idletasks()
    enable_click_through(root, transparent_color)

    canvas = tk.Canvas(
        root,
        width=screen_width,
        height=screen_height,
        highlightthickness=0,
        bg=transparent_color,
    )
    canvas.pack(fill=tk.BOTH, expand=True)

    half = sample_size // 2
    center_x = screen_width // 2
    center_y = screen_height // 2
    left = center_x - half
    top = center_y - half
    right = left + sample_size
    bottom = top + sample_size
    rect_id = canvas.create_rectangle(left, top, right, bottom, outline="cyan", width=2)

    status_label = tk.Label(
        root,
        text="",
        bg="black",
        fg="green",
        font=("Arial", 12, "bold"),
        justify="left",
    )
    status_label.place(x=10, y=10)
    return root, canvas, status_label, rect_id


def update_overlay(status_label: tk.Label, canvas: tk.Canvas, rect_id: int, state: State) -> None:
    status_text = (
        f"Enable: {'ON' if state.enabled else 'OFF'}\n"
        f"Detected: {'YES' if state.detected else 'NO'}\n"
        f"Triggers: {state.trigger_count}\n"
        f"Test Clicks: {state.test_count}\n"
        f"Left Tests: {state.left_test_count}"
    )
    status_label.config(text=status_text)
    status_label.config(fg="green")
    if state.indicator_color == "yellow":
        canvas.itemconfig(rect_id, outline="yellow")
    elif state.indicator_color == "red":
        canvas.itemconfig(rect_id, outline="red")
    else:
        canvas.itemconfig(rect_id, outline="cyan")


def listen_toggle_key(state: State, toggle_key: str, test_key: str, test_left_key: str) -> None:
    def on_press(key):
        try:
            if key == keyboard.Key[toggle_key]:
                state.enabled = not state.enabled
                return
            if key == keyboard.Key[test_key]:
                click_middle()
                state.test_count += 1
                return
            if key == keyboard.Key[test_left_key]:
                click_left()
                state.left_test_count += 1
                return
        except KeyError:
            if hasattr(key, "char") and key.char == toggle_key:
                state.enabled = not state.enabled
            elif hasattr(key, "char") and key.char == test_key:
                click_middle()
                state.test_count += 1
            elif hasattr(key, "char") and key.char == test_left_key:
                click_left()
                state.left_test_count += 1

    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()


def main() -> None:
    args = parse_args()
    state = State()
    set_dpi_awareness()

    with mss.mss() as sct:
        monitor_index = 1 if len(sct.monitors) > 1 else 0
        monitor = sct.monitors[monitor_index]
        overlay_root, canvas, status_label, rect_id = build_overlay(args.sample_size, monitor)

        toggle_thread = threading.Thread(
            target=listen_toggle_key,
            args=(
                state,
                args.toggle_key.lower(),
                args.test_key.lower(),
                args.test_left_key.lower(),
            ),
            daemon=True,
        )
        toggle_thread.start()

        def loop() -> None:
            center_x = monitor["width"] // 2
            center_y = monitor["height"] // 2
            half = args.sample_size // 2
            bbox = {
                "left": monitor.get("left", 0) + max(center_x - half, 0),
                "top": monitor.get("top", 0) + max(center_y - half, 0),
                "width": args.sample_size,
                "height": args.sample_size,
            }
            frame_interval = 1.0 / max(args.fps, 1.0)
            while True:
                if state.enabled:
                    screenshot = sct.grab(bbox)
                    detected = region_contains_gold(
                        screenshot.raw,
                        args.hue_min,
                        args.hue_max,
                        args.sat_min,
                        args.val_min,
                    )
                    if detected:
                        if not state.detected:
                            click_middle()
                            state.trigger_count += 1
                        state.indicator_color = "red"
                    else:
                        if state.detected:
                            click_middle()
                            state.trigger_count += 1
                        state.indicator_color = "green"
                    state.detected = detected
                else:
                    state.detected = False
                    state.indicator_color = "green"

                update_overlay(status_label, canvas, rect_id, state)
                overlay_root.update_idletasks()
                overlay_root.update()
                time.sleep(frame_interval)

        loop()


if __name__ == "__main__":
    main()
