@echo off
REM ============================================================
REM  dev-ai-skills 一鍵更新啟動器 (Windows)
REM  雙擊執行：git pull + 重新安裝所有偵測到的 AI 工具版本
REM ============================================================

REM 切換到 .bat 自己所在的資料夾（不論被放在哪裡 clone）
cd /d "%~dp0"

echo ============================================================
echo  Step 1/2: git pull 拉取最新 source
echo ============================================================
git pull
if errorlevel 1 (
    echo.
    echo [error] git pull 失敗，請確認網路或衝突狀況後再試。
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Step 2/2: 執行 install.ps1 ^(auto 模式^)
echo ============================================================
powershell -ExecutionPolicy Bypass -File "%~dp0install.ps1"
if errorlevel 1 (
    echo.
    echo [error] install.ps1 失敗，請查看上方訊息。
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  All done! 按任意鍵關閉視窗。
echo ============================================================
pause
