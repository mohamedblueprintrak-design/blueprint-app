@echo off
title BluePrint Engineering OS - Launcher
echo ========================================
echo    تشغيل BluePrint Engineering OS
echo ========================================
echo.
echo [1] بدء تشغيل الخادم الخلفي (FastAPI)...
start "BluePrint Server" cmd /k "cd /d %~dp0 && uvicorn main:app --reload --host 0.0.0.0
timeout /t 3 /nobreak >nul

echo [2] بدء تشغيل الواجهة الأمامية (Streamlit)...
start "BluePrint UI" cmd /k "cd /d %~dp0 && streamlit run gateway.py --server.address 0.0.0.0

echo.
echo ✅ تم بدء تشغيل جميع المكونات.
echo الخادم: http://127.0.0.1:8000
echo الواجهة: http://localhost:8501
echo.
echo يرجى عدم إغلاق هذه النافذة.
pause