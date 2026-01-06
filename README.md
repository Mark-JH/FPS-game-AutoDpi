# Logitech-FPS-game-AutoDpi

本仓库提供一个可直接粘贴到 **Logitech G Hub** 的 Lua 脚本，用于检测屏幕中心 10 像素范围的颜色，当检测到金色或近似颜色时，将鼠标 DPI 调整为 1000。

## 使用方式
1. 打开 Logitech G Hub。
2. 选择你的鼠标配置文件。
3. 打开“脚本”并创建新脚本。
4. 将 `auto_dpi.lua` 的内容粘贴进去并保存。
5. 根据需要修改脚本顶部 `config` 中的阈值与 DPI。

## 调参建议
- `sampleSize`：采样区域边长（像素），默认 10。
- `targetDPI`：检测到目标颜色时切换的 DPI，默认 1000。
- `defaultDPI`：关闭自动检测后恢复的 DPI。
- `gold`：金色 RGB 阈值范围，可根据游戏画面调整。
- `toggleButton`：开关按钮，G502 Lightspeed 侧键2 通常为鼠标按钮 5。

> 注意：G Hub 的 Lua 脚本只能在 Logitech 支持的设备上运行。
