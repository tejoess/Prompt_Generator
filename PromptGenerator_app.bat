@echo off
title Prompt Generator App
cd /d C:\prompt_generator_app
call venv\Scripts\activate
start http://127.0.0.1:8000
python run.py
pause