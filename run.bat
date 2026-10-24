@echo off
rem 双击静默启动：不装东西不打字，直接藏后台运行
pythonw -m pip install -q -r "%~dp0requirements.txt" >nul 2>nul
start /min "" pythonw "%~dp0app.py"
