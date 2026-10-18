@echo off
cd /d d:\mindful\workwell
echo Frontend URL: http://localhost:5173
echo Backend URL: http://localhost:8000
start "Frontend Tunnel" cmd /k "cloudflared tunnel --protocol http2 --url http://localhost:5173"
start "Backend Tunnel" cmd /k "cloudflared tunnel --protocol http2 --url http://localhost:8000"
