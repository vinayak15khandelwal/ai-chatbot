# Deployment guide (you deploy; nothing here has been deployed for you)

Recommended: **backend on Render (Docker web service + persistent disk)**, **frontend on Vercel**.

## Important: persistent disk on Render
Render persistent disks are only available on **paid** web services; the Free instance type has no disk, so SQLite
history would be lost on every restart/redeploy. Use a paid instance (e.g. Starter) with a disk for real persistence
(source: Render docs, "Persistent Disks"). Alternatives with volumes are Railway or Fly.io (check their current pricing/docs).
If you accept losing history on restart, Free works for a demo, but then say so in your README.

## 0. Push to GitHub
```bash
cd <repo root>
git init && git add . && git commit -m "LLM chatbot"
git branch -M main && git remote add origin <YOUR_REPO_URL> && git push -u origin main
```
Check first that `git status` shows no `.env`, `*.db`, `node_modules` (all are in `.gitignore`).

## 1. Backend on Render
1. Render dashboard → **New → Web Service** → connect the repo.
2. **Language/Runtime: Docker**. **Root Directory:** `backend` (Dockerfile path `./Dockerfile`). No build/start command needed; the image starts uvicorn on `$PORT`.
3. **Instance type:** paid (needed for a disk).
4. **Advanced → Add Disk:** name `data`, **mount path `/data`**, size 1 GB.
5. **Health Check Path:** `/health`
6. **Environment variables:**

| Key | Value |
|---|---|
| `LLM_API_KEYS` | `key1,key2` (your real keys, comma-separated) |
| `LLM_MODEL` | e.g. `gemini/gemini-3.8-flash` |
| `DATABASE_URL` | `sqlite:////data/app.db` |
| `ALLOWED_ORIGINS` | your frontend URL, e.g. `https://your-app.vercel.app` (no trailing slash; comma-separate several). Set after step 2, then redeploy |
| `ENABLE_FAILURE_SIMULATION` | `true` (required by the assignment) |

7. Deploy, then open `https://<backend>.onrender.com/health` → `{"status":"ok","keys_configured":2,"cache_enabled":true}`.

## 2. Frontend on Vercel
1. Vercel → **Add New → Project** → import the repo.
2. **Root Directory:** `frontend`. Framework preset: Vite.
3. **Build command:** `npm run build` · **Output directory:** `dist` · Install: `npm install`.
4. **Environment variable:** `VITE_API_BASE_URL` = your backend URL, e.g. `https://<backend>.onrender.com` (no trailing slash). It is baked in at build time, so change it → redeploy.
5. Deploy, copy the Vercel URL into the backend's `ALLOWED_ORIGINS`, and redeploy the backend.

(Netlify/Cloudflare Pages work the same: build `npm run build`, publish `dist`, same env var.)

## 3. Verify the live app
```bash
API=https://<backend>.onrender.com
curl -s $API/health
curl -s $API/chat -H 'Content-Type: application/json' -d '{"session_id":"v1","message":"hi"}'
curl -s $API/chat -H 'Content-Type: application/json' -H 'X-Simulate-Failure: key_1=429' -d '{"session_id":"v2","message":"hello"}'
```
Then open the frontend: send a message, check the metadata, use Settings → simulate failure, and confirm there is no CORS error in the browser console. Redeploy the backend and confirm `GET /sessions/v1/messages` still returns history (disk works).
