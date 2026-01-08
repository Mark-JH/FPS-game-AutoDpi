import argparse
import colorsys
import ctypes
import subprocess
import threading
import time
import tkinter as tk
from dataclasses import dataclass

import mss
from pynput import keyboard


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "检测屏幕中心区域的颜色，当出现金色或近似颜色时，将 DPI 切换到目标值，并在屏幕显示状态。"
        )
    )
    parser.add_argument("--sample-size", type=int, default=10, help="采样区域边长（像素）")
    parser.add_argument("--target-dpi", type=int, default=500, help="检测到目标颜色时切换到的 DPI")
    parser.add_argument("--default-dpi", type=int, default=2000, help="未触发时使用的 DPI")
    parser.add_argument("--fps", type=float, default=100.0, help="检测频率（每秒次数）")
    parser.add_argument("--cooldown", type=float, default=0.5, help="触发冷却时间（秒）")
    parser.add_argument("--toggle-key", type=str, default="f8", help="启用/禁用检测的按键（例如 f8）")
    parser.add_argument(
        "--dpi-command",
        type=str,
        default="",
        help="设置 DPI 的命令模板，使用 {dpi} 作为占位符",
    )
    parser.add_argument("--hue-min", type=float, default=35.0, help="金色最小色相（度）")
    parser.add_argument("--hue-max", type=float, default=60.0, help="金色最大色相（度）")
    parser.add_argument("--sat-min", type=float, default=0.4, help="金色最小饱和度（0-1）")
    parser.add_argument("--val-min", type=float, default=0.4, help="金色最小亮度（0-1）")
    return parser.parse_args()


@dataclass
class State:
    enabled: bool = True
    current_dpi: int = 2000
    last_trigger: float = 0.0
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


def run_dpi_command(template: str, dpi: int) -> None:
    if not template:
        return
    command = template.format(dpi=dpi)
    subprocess.run(command, shell=True, check=False)


def press_key(key_name: str) -> None:
    controller = keyboard.Controller()
    key = getattr(keyboard.Key, key_name, None)
    if key is None:
        if key_name.startswith("f") and key_name[1:].isdigit():
            f_number = int(key_name[1:])
            if 13 <= f_number <= 24:
                # Virtual-key codes: F1=0x70, F24=0x87.
                vk = 0x6F + f_number
                keycode = keyboard.KeyCode.from_vk(vk)
                controller.press(keycode)
                controller.release(keycode)
                return
        controller.press(key_name)
        controller.release(key_name)
        return
    controller.press(key)
    controller.release(key)


def set_dpi_awareness() -> None:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
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
        f"Current DPI: {state.current_dpi}"
    )
    status_label.config(text=status_text)
    status_label.config(fg="green")
    if state.indicator_color == "yellow":
        canvas.itemconfig(rect_id, outline="yellow")
    elif state.indicator_color == "red":
        canvas.itemconfig(rect_id, outline="red")
    else:
        canvas.itemconfig(rect_id, outline="cyan")


def listen_toggle_key(state: State, toggle_key: str) -> None:
    def on_press(key):
        try:
            if key == keyboard.Key[toggle_key]:
                state.enabled = not state.enabled
                return
        except KeyError:
            if hasattr(key, "char") and key.char == toggle_key:
                state.enabled = not state.enabled

    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()


def main() -> None:
    args = parse_args()
    state = State(current_dpi=args.default_dpi)
    set_dpi_awareness()

    with mss.mss() as sct:
        monitor_index = 1 if len(sct.monitors) > 1 else 0
        monitor = sct.monitors[monitor_index]
        overlay_root, canvas, status_label, rect_id = build_overlay(args.sample_size, monitor)

        toggle_thread = threading.Thread(
            target=listen_toggle_key, args=(state, args.toggle_key.lower()), daemon=True
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
                    if region_contains_gold(
                        screenshot.raw,
                        args.hue_min,
                        args.hue_max,
                        args.sat_min,
                        args.val_min,
                    ):
                        now = time.time()
                        if now - state.last_trigger >= args.cooldown:
                            state.indicator_color = "yellow"
                            if state.current_dpi != args.target_dpi:
                                run_dpi_command(args.dpi_command, args.target_dpi)
                                state.current_dpi = args.target_dpi
                                press_key("f20")
                            state.indicator_color = "red"
                            state.last_trigger = now
                    else:
                        if state.current_dpi != args.default_dpi:
                            run_dpi_command(args.dpi_command, args.default_dpi)
                            state.current_dpi = args.default_dpi
                            press_key("f21")
                        state.indicator_color = "green"
                else:
                    if state.current_dpi != args.default_dpi:
                        run_dpi_command(args.dpi_command, args.default_dpi)
                        state.current_dpi = args.default_dpi
                        press_key("f21")
                    state.indicator_color = "green"

                update_overlay(status_label, canvas, rect_id, state)
                overlay_root.update_idletasks()
                overlay_root.update()
                time.sleep(frame_interval)

        loop()


if __name__ == "__main__":
    main()
