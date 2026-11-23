@echo off
rem Launcher: au05 show | au05 apply | au05 set key1 "Ctrl+Alt+L"   (runs from any folder via uv)
uv run --quiet --project "%~dp0." au05 %*
