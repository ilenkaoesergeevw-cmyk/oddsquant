@echo off
set NODE_OPTIONS=
cd /d "%~dp0"
if not exist node_modules npm install
npm start
pause
