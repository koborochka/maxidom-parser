@echo off
echo Stopping all processes using port 8000...

for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000') do (
    echo Terminating process with PID %%a...
    taskkill /PID %%a /F >nul 2>&1
)

echo All processes using port 8000 have been terminated.
pause
