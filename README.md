# Logitech-FPS-game-AutoDpi

本仓库提供一个 **Python** 脚本，用于检测屏幕中心 10 像素范围的颜色，当检测到金色或近似颜色时，降低鼠标 DPI 到目标值，并在屏幕上显示状态与识别区域。

## 功能
- 在屏幕中心绘制识别区域。
- 识别到金色时将状态颜色显示为黄色，并切换 DPI 到目标值（默认 500）。
- DPI 切换到目标值后状态颜色显示为红色；常态为绿色。
- 左上角常驻显示：是否启用检测 + 当前 DPI。
- 支持按键开关（默认 F8）切换检测状态。

> 说明：脚本无法直接控制罗技鼠标灯光颜色，因此用屏幕状态颜色提示代替。如果你有可用的 DPI/灯光控制工具，可通过 `--dpi-command` 自行接入。

## 使用方式
```bash
python auto_dpi.py
```

## 安装依赖
```bash
pip install -r requirements.txt
```

## 参数说明
- `--sample-size`：采样区域边长（像素），默认 10。
- `--target-dpi`：检测到目标颜色时切换到的 DPI（降低 DPI），默认 500。
- `--default-dpi`：未触发时使用的 DPI，默认 2000。
- `--fps`：检测频率（每秒次数），默认 100。
- `--cooldown`：触发冷却时间（秒），默认 0.5。
- `--toggle-key`：启用/禁用检测的按键，默认 `f8`。
- `--dpi-command`：设置 DPI 的外部命令模板，例如 `--dpi-command "path/to/cli set-dpi {dpi}"`。
- `--hue-min/--hue-max/--sat-min/--val-min`：金色 HSV 阈值。

## 识别区域
脚本会在屏幕中央绘制一个矩形框用于显示识别区域。
