@echo off
chcp 65001 >nul
title INDAGO Forense — Servidor

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║   INDAGO Forense — Servidor de Captura   ║
echo  ╚══════════════════════════════════════════╝
echo.

cd /d "%~dp0"

:: Check if Python is available
where python >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python no encontrado.
    echo  Instale Python 3.9+ desde https://python.org
    echo  Asegurese de marcar "Add Python to PATH" durante la instalacion.
    pause
    exit /b 1
)

:: Create virtual environment if it doesn't exist
if not exist "server-venv\Scripts\activate.bat" (
    echo  [1/3] Creando entorno virtual Python...
    python -m venv server-venv
    if errorlevel 1 (
        echo  [ERROR] No se pudo crear el entorno virtual.
        pause
        exit /b 1
    )
    echo  [OK] Entorno virtual creado.
    echo.

    echo  [2/3] Instalando dependencias...
    call server-venv\Scripts\activate.bat
    pip install --upgrade pip -q
    pip install flask flask-cors yt-dlp requests -q
    echo  [OK] Flask, yt-dlp y requests instalados.
    echo.

    echo  [opcional] Instalando Playwright para capturas automaticas...
    pip install playwright -q
    python -m playwright install chromium 2>nul && (
        echo  [OK] Playwright instalado.
    ) || (
        echo  [AVISO] Playwright omitido - las capturas de pantalla seran manuales.
    )
    echo.
) else (
    echo  [OK] Entorno virtual encontrado.
    call server-venv\Scripts\activate.bat
)

echo  [3/3] Iniciando servidor...
echo.
echo  Abra su navegador en:
echo    http://localhost:8765
echo.
echo  Para conectarse desde otras maquinas use la IP de este equipo:
echo    http://[IP-DE-ESTE-EQUIPO]:8765
echo.
echo  Presione Ctrl+C para detener el servidor.
echo.

python server.py

echo.
echo  Servidor detenido.
pause
