@echo off
mode con: cols=60 lines=15
color 0A
echo.
echo        ***************************************
echo        *                                     *
echo        *       Engineering OS is Loading     *
echo        *                                     *
echo        ***************************************
echo.
timeout /t 2 >nul

start "" "C:\Users\Dell\Desktop\engineering-os-ai\run_all.bat"
exit
