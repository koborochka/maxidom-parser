@echo off
echo Starting FastAPI server...
start /B python -X utf8 -m uvicorn main:app > server.log 2>&1