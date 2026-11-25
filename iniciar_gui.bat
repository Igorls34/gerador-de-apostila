@echo off
title Gerador de Apostilas em PDF
cd /d "%~dp0"
python app_gui.py
if %errorlevel% neq 0 (
    echo.
    echo Ocorreu um erro ao iniciar a aplicacao.
    pause
)
