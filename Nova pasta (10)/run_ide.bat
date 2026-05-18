@echo off
setlocal enabledelayedexpansion

rem Definir diretório do script
cd /d "%~dp0"

rem Encontrar Python disponível
set "PYEXEC="
where /q py.exe
if %ERRORLEVEL% EQU 0 (
    set "PYEXEC=py -3"
) else (
    where /q python.exe
    if %ERRORLEVEL% EQU 0 (
        set "PYEXEC=python"
    )
)

if not defined PYEXEC (
    echo Python nao encontrado no PATH. Instale o Python 3 e execute novamente.
    pause
    exit /b 1
)

rem Criar venv se necessario
if not exist "venv\Scripts\python.exe" (
    echo Criando ambiente virtual em venv...
    %PYEXEC% -m venv "venv"
    if errorlevel 1 (
        echo Falha ao criar o ambiente virtual.
        pause
        exit /b 1
    )
)

rem Usar Python do venv
set "PYEXEC=%~dp0venv\Scripts\python.exe"

if not exist "%PYEXEC%" (
    echo Nao foi possivel encontrar o Python no ambiente virtual.
    pause
    exit /b 1
)

rem Atualizar pip e instalar dependencias
echo Instalando dependencias... Isso pode demorar alguns minutos.
"%PYEXEC%" -m pip install --upgrade pip
if errorlevel 1 (
    echo Falha ao atualizar o pip.
    pause
    exit /b 1
)
"%PYEXEC%" -m pip install -r requirements.txt --progress-bar off
if errorlevel 1 (
    echo Falha ao instalar as dependencias.
    pause
    exit /b 1
)

echo Dependencias instaladas com sucesso.
echo Iniciando CookieScript IDE...
"%PYEXEC%" cookie_ide_app.py
endlocal
