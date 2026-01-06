-- Logitech G Hub Lua script: auto DPI switcher based on center screen color.
-- 将该脚本粘贴到 G Hub 的 Lua 脚本编辑器中使用。

local config = {
    sampleSize = 10,        -- 采样区域边长（像素）
    targetDPI = 1000,       -- 检测到目标颜色时切换到的 DPI
    pollIntervalMs = 33,    -- 检测间隔（毫秒）约 30 FPS
    cooldownMs = 500,       -- 冷却时间（毫秒）避免频繁切换
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

function OnEvent(event, arg)
    if event == "PROFILE_ACTIVATED" then
        EnablePrimaryMouseButtonEvents(true)
    end

    if event ~= "PROFILE_ACTIVATED" and event ~= "PROFILE_DEACTIVATED" then
        return
    end

    if event == "PROFILE_ACTIVATED" then
        local screenWidth, screenHeight = GetScreenSize()
        local half = math.floor(config.sampleSize / 2)
        local centerX = clamp(math.floor(screenWidth / 2) - half, 0, screenWidth - config.sampleSize)
        local centerY = clamp(math.floor(screenHeight / 2) - half, 0, screenHeight - config.sampleSize)

        while true do
            if regionContainsGold(centerX, centerY, config.sampleSize) then
                local nowMs = GetRunningTime()
                if nowMs - lastTriggerMs >= config.cooldownMs then
                    SetMouseDPI(config.targetDPI)
                    lastTriggerMs = nowMs
                end
            end
            Sleep(config.pollIntervalMs)
        end
    end
end
