-- Logitech G Hub Lua script: auto DPI switcher based on center screen color.
-- 将该脚本粘贴到 G Hub 的 Lua 脚本编辑器中使用。

local config = {
    sampleSize = 10,        -- 采样区域边长（像素）
    targetDPI = 500,        -- 检测到目标颜色时切换到的 DPI
    defaultDPI = 2000,      -- 关闭自动检测后恢复的 DPI
    pollIntervalMs = 10,    -- 检测间隔（毫秒）约 100 FPS
    cooldownMs = 500,       -- 冷却时间（毫秒）避免频繁切换
    toggleButton = 4,       -- 侧键2: G502 Lightspeed 默认是鼠标按钮4
    -- 金色/近似金色的 RGB 阈值范围（可根据游戏画面调整）
    gold = {
        rMin = 180,
        rMax = 255,
        gMin = 140,
        gMax = 220,
        bMin = 40,
        bMax = 140,
    },
}

local lastTriggerMs = 0
local lastToggleState = false
local autoEnabled = true
local lightState = ""

local function clamp(value, minValue, maxValue)
    if value < minValue then
        return minValue
    end
    if value > maxValue then
        return maxValue
    end
    return value
end

local function parseHexColor(hex)
    -- hex 格式: "RRGGBB"
    local r = tonumber(string.sub(hex, 1, 2), 16)
    local g = tonumber(string.sub(hex, 3, 4), 16)
    local b = tonumber(string.sub(hex, 5, 6), 16)
    return r, g, b
end

local function isGoldLike(r, g, b)
    return r >= config.gold.rMin and r <= config.gold.rMax
        and g >= config.gold.gMin and g <= config.gold.gMax
        and b >= config.gold.bMin and b <= config.gold.bMax
end

local function regionContainsGold(x, y, size)
    for offsetY = 0, size - 1 do
        for offsetX = 0, size - 1 do
            local hex = GetPixelColor(x + offsetX, y + offsetY)
            local r, g, b = parseHexColor(hex)
            if isGoldLike(r, g, b) then
                return true
            end
        end
    end
    return false
end

local function setBacklight(r, g, b, state)
    if lightState == state then
        return
    end
    SetBacklightColor(r, g, b)
    lightState = state
end

local function setLightGreen()
    setBacklight(0, 255, 0, "green")
end

local function setLightYellow()
    setBacklight(255, 255, 0, "yellow")
end

local function setLightRed()
    setBacklight(255, 0, 0, "red")
end

function OnEvent(event, arg)
    if event == "PROFILE_ACTIVATED" then
        EnablePrimaryMouseButtonEvents(true)
    end

    if event ~= "PROFILE_ACTIVATED" and event ~= "PROFILE_DEACTIVATED" then
        return
    end

    if event == "PROFILE_ACTIVATED" then
        setLightGreen()
        local screenWidth, screenHeight = GetScreenSize()
        local half = math.floor(config.sampleSize / 2)
        local centerX = clamp(math.floor(screenWidth / 2) - half, 0, screenWidth - config.sampleSize)
        local centerY = clamp(math.floor(screenHeight / 2) - half, 0, screenHeight - config.sampleSize)

        while true do
            local togglePressed = IsMouseButtonPressed(config.toggleButton)
            if togglePressed and not lastToggleState then
                autoEnabled = not autoEnabled
                if autoEnabled then
                    SetMouseDPI(config.targetDPI)
                    setLightRed()
                else
                    SetMouseDPI(config.defaultDPI)
                    setLightGreen()
                end
            end
            lastToggleState = togglePressed

            if autoEnabled and regionContainsGold(centerX, centerY, config.sampleSize) then
                local nowMs = GetRunningTime()
                if nowMs - lastTriggerMs >= config.cooldownMs then
                    setLightYellow()
                    SetMouseDPI(config.targetDPI)
                    setLightRed()
                    lastTriggerMs = nowMs
                end
            end
            Sleep(config.pollIntervalMs)
        end
    end
end
