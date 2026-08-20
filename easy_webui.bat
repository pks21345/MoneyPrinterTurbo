@echo off
setlocal
chcp 65001 >nul

set "CURRENT_DIR=%~dp0"
cd /d "%CURRENT_DIR%"
set "PYTHONPATH=%CURRENT_DIR%"

if not defined MPT_EASY_HOST set "MPT_EASY_HOST=127.0.0.1"
if not defined MPT_EASY_PORT set "MPT_EASY_PORT=8501"

set "STREAMLIT_CMD="
if exist "%CURRENT_DIR%\.venv\Scripts\python.exe" (
    set "STREAMLIT_CMD="%CURRENT_DIR%\.venv\Scripts\python.exe" -m streamlit"
) else if exist "%CURRENT_DIR%\lib\python\python.exe" (
    set "STREAMLIT_CMD="%CURRENT_DIR%\lib\python\python.exe" -m streamlit"
) else (
    where uv >nul 2>nul
    if not errorlevel 1 set "STREAMLIT_CMD=uv run streamlit"
)

if not defined STREAMLIT_CMD (
    where streamlit >nul 2>nul
    if not errorlevel 1 (
        echo ***** Warning: using streamlit from PATH. If dependencies fail, run 'uv sync --frozen' first. *****
        set "STREAMLIT_CMD=streamlit"
    )
)

if not defined STREAMLIT_CMD (
    echo ***** MPT Easy could not find project Python, uv, or streamlit. *****
    echo ***** Install the project dependencies first, then run this launcher again. *****
    pause
    exit /b 1
)

set "SELECTED_EASY_PORT="
for /f %%P in ('powershell -NoProfile -ExecutionPolicy Bypass -Command "$hostAddress=$null; foreach ($address in [Net.Dns]::GetHostAddresses($env:MPT_EASY_HOST)) { if ($address.AddressFamily -eq [Net.Sockets.AddressFamily]::InterNetwork) { $hostAddress=$address; break } }; if ($null -eq $hostAddress) { exit 1 }; $preferred=[int]$env:MPT_EASY_PORT; $candidates=New-Object System.Collections.Generic.List[int]; $candidates.Add($preferred); foreach ($candidate in 8502..8599) { if ($candidate -ne $preferred) { $candidates.Add($candidate) } }; foreach ($port in $candidates) { $socket=[Net.Sockets.Socket]::new([Net.Sockets.AddressFamily]::InterNetwork,[Net.Sockets.SocketType]::Stream,[Net.Sockets.ProtocolType]::Tcp); try { $socket.Bind([Net.IPEndPoint]::new($hostAddress,$port)); $socket.Close(); Write-Output $port; exit 0 } catch { try { $socket.Close() } catch {} } }; exit 1"') do set "SELECTED_EASY_PORT=%%P"

if not defined SELECTED_EASY_PORT (
    echo ***** MPT Easy could not find an available port in 8501-8599 for %MPT_EASY_HOST%. *****
    pause
    exit /b 1
)

if not "%SELECTED_EASY_PORT%"=="%MPT_EASY_PORT%" (
    echo ***** Port %MPT_EASY_PORT% is busy; MPT Easy will use %SELECTED_EASY_PORT%. *****
)
set "MPT_EASY_PORT=%SELECTED_EASY_PORT%"
set "MPT_EASY_URL=http://%MPT_EASY_HOST%:%MPT_EASY_PORT%"

echo ***** MPT Easy: %MPT_EASY_URL% *****
start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 2; Start-Process '%MPT_EASY_URL%'"

%STREAMLIT_CMD% run .\webui\easy\App.py --server.address=%MPT_EASY_HOST% --server.port=%MPT_EASY_PORT% --browser.serverAddress=%MPT_EASY_HOST% --browser.gatherUsageStats=False --client.toolbarMode=minimal --logger.hideWelcomeMessage=True --server.showEmailPrompt=False --server.enableCORS=True
