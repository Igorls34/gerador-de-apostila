@echo off
title Gerador de Apostilas • Web Studio
cd /d "%~dp0"
echo Iniciando o Web Studio...
python app_web.py
if %errorlevel% neq 0 (
    echo.
    echo Ocorreu um erro ao iniciar a aplicacao Web.
    pause
)
