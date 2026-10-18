# Cloudflare mobile testing setup

This project is configured to run locally on a laptop and be exposed temporarily through Cloudflare Quick Tunnels for mobile testing.

## 1) Start the backend

```powershell
cd d:\mindful\workwell\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verify the local API:

```powershell
http://localhost:8000/health
http://localhost:8000/docs
```

## 2) Start the frontend

```powershell
cd d:\mindful\workwell
npm install
npm run dev -- --host 0.0.0.0
```

Verify the local frontend:

```powershell
http://localhost:5173
```

## 3) Start the backend Cloudflare tunnel

```powershell
cloudflared tunnel --url http://localhost:8000
```

This will print a temporary HTTPS URL such as:

```text
https://backend-random.trycloudflare.com
```

## 4) Start the frontend Cloudflare tunnel

```powershell
cloudflared tunnel --url http://localhost:5173
```

This will print a temporary HTTPS URL such as:

```text
https://frontend-random.trycloudflare.com
```

## 5) Update the frontend API environment variable

Create or edit `.env.local` in the project root:

```env
VITE_API_BASE_URL=https://<backend-cloudflare-url>
```

Then restart the frontend:

```powershell
cd d:\mindful\workwell
npm run dev -- --host 0.0.0.0
```

The frontend must never call `http://localhost:8000` from the public mobile browser, because `localhost` on a phone points to the phone itself.

## 6) Open the frontend Cloudflare URL on mobile

Open the public frontend URL on the phone and verify the landing page loads. The app should remain on the public landing page instead of redirecting to a login or dashboard before the user selects an action.

## 7) Troubleshooting

- Ensure the backend is running and reachable on `http://localhost:8000`.
- Ensure the frontend is bound to `0.0.0.0`.
- Ensure the frontend tunnel is the one used for the mobile browser.
- Ensure `VITE_API_BASE_URL` points to the backend tunnel URL, not localhost.
- Confirm the backend CORS configuration includes the public frontend origin.
- Check browser network requests for `https://<backend-cloudflare-url>` and not `localhost`.

## 8) Optional helper scripts

### start-dev.bat

```bat
@echo off
cd /d d:\mindful\workwell
start "Frontend" cmd /k "npm run dev -- --host 0.0.0.0"
cd backend
start "Backend" cmd /k "python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
```

### start-cloudflare.bat

```bat
@echo off
cd /d d:\mindful\workwell
echo Frontend URL: http://localhost:5173
echo Backend URL: http://localhost:8000
start "Frontend Tunnel" cmd /k "cloudflared tunnel --url http://localhost:5173"
start "Backend Tunnel" cmd /k "cloudflared tunnel --url http://localhost:8000"
```
