# Deploying the Project on Vercel

This guide explains how to deploy the **Conversational Automotive Parts Sourcing Agent** with **Vercel**.

---

## 1. Architecture Overview

This project consists of two core layers:

| Layer | Technology | Recommended Host | Why? |
|---|---|---|---|
| **Frontend** | React 18, Vite, Tailwind CSS | **Vercel** | Ultra-fast global Edge CDN, automatic CI/CD, ideal for Vite SPAs. |
| **Backend** | Python 3.10+, FastAPI, LangGraph, Playwright (Chromium), SSE | **Render / Railway / Fly.io / VPS** | Requires persistent headless Chromium browser sessions, long execution times (15–45s per scrape), and sustained Server-Sent Events (SSE). |

> [!IMPORTANT]
> **Can the backend run on Vercel Serverless Functions?**
> **No.** Vercel Serverless Functions are stateless and enforce strict limitations:
> 1. **Bundle Size Limit**: 50 MB zipped (Playwright's Chromium browser is ~280 MB+).
> 2. **Execution Timeout**: 10s default limit on Hobby plan (multi-supplier scraping takes 15–45s).
> 3. **Persistent Browser Sessions**: The agent maintains active Chromium tabs open across conversational turns (asking mechanic follow-up questions). Serverless functions terminate immediately after each request.
> 
> Therefore, the **frontend is deployed to Vercel**, and the **backend is deployed to a persistent container service** (like Render, Railway, or Fly.io). The frontend communicates with the backend via `VITE_API_URL`.

---

## 2. Deploying Frontend to Vercel

### Method A: Via Vercel Web Dashboard (Recommended)

1. **Push your code to GitHub**:
   ```bash
   git add .
   git commit -m "Configure Vercel and backend Docker deployment"
   git push origin master
   ```

2. **Import into Vercel**:
   - Go to [vercel.com/new](https://vercel.com/new).
   - Sign in with your GitHub account.
   - Select the repository: `Pulkit9070/Sourcing-Agent` (or your fork).

3. **Configure Project Settings**:
   - **Framework Preset**: `Vite`
   - **Root Directory**: Click *Edit* and select `frontend` (or leave default if using root `vercel.json`).
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
   - **Install Command**: `npm install`

4. **Set Environment Variables**:
   Under **Environment Variables**, add:
   - **Key**: `VITE_API_URL`
   - **Value**: `https://<your-backend-service-url>` (e.g. `https://cas-backend.onrender.com` or your deployed backend URL).
   *(If you haven't deployed the backend yet, you can leave it blank initially or add it after deploying the backend).*

5. **Deploy**:
   - Click **Deploy**. Vercel will build and publish your frontend at `https://<your-project>.vercel.app`.

---

### Method B: Via Vercel CLI

1. Log in to Vercel CLI:
   ```bash
   npx vercel login
   ```

2. Deploy the frontend:
   ```bash
   cd frontend
   npx vercel
   ```
   Follow the interactive prompts:
   - *Set up and deploy?* **Y**
   - *Which scope?* Select your account
   - *Link to existing project?* **N**
   - *What's your project's name?* `parts-sourcing-dashboard`
   - *In which directory is your code located?* `./`

3. Set the production backend URL:
   ```bash
   npx vercel env add VITE_API_URL production
   # Enter your deployed backend URL: https://your-backend.railway.app
   ```

4. Deploy to production:
   ```bash
   npx vercel --prod
   ```

---

## 3. Deploying the Backend (Container Host)

We have provided a ready-to-run [Dockerfile](file:///home/habilelabs/Development/CAS/backend/Dockerfile) in `backend/` that installs Python, Playwright, and Chromium dependencies.

### Option 1: Render.com (Free / Easy)

1. Go to [dashboard.render.com](https://dashboard.render.com/) and click **New +** -> **Web Service**.
2. Connect your GitHub repository.
3. Configure the service:
   - **Name**: `cas-backend`
   - **Root Directory**: `backend`
   - **Environment**: `Docker`
   - **Dockerfile Path**: `Dockerfile`
4. Add Environment Variables (from [backend/.env.example](file:///home/habilelabs/Development/CAS/backend/.env.example)):
   - `GEMINI_API_KEY`: `<your_gemini_api_key>`
   - `GEMINI_MODEL`: `gemini-2.5-flash`
   - `GEMINI_FALLBACK_MODELS`: `gemini-2.5-flash,gemini-1.5-flash`
   - `GEMINI_TIMEOUT_MS`: `15000`
5. Click **Create Web Service**. Once deployed, copy your Render URL (e.g., `https://cas-backend.onrender.com`).
6. Update `VITE_API_URL` in your Vercel project settings with this URL!

---

### Option 2: Railway.app

1. Go to [railway.app](https://railway.app/) and create a **New Project** -> **Deploy from GitHub repo**.
2. Go to **Settings** -> **Root Directory**, set it to `/backend`.
3. Railway automatically detects `backend/Dockerfile` and installs Playwright with Chromium.
4. In **Variables**, add:
   - `GEMINI_API_KEY`
   - `PORT`: `8000`
5. Go to **Settings** -> **Networking** -> **Generate Domain** to get your public backend URL.
6. Set that public URL as `VITE_API_URL` in Vercel.

---

### Option 3: Self-Hosted Docker / VPS (AWS, DigitalOcean, Hetzner)

You can run the backend directly on any VM using the included `docker-compose.yml`:

```bash
# Clone the repository onto your server
git clone https://github.com/Pulkit9070/Sourcing-Agent.git
cd Sourcing-Agent

# Set your Gemini API key in backend/.env
cp backend/.env.example backend/.env
nano backend/.env

# Build and start container in background
docker compose up -d --build
```
The backend will run on port `8000`. Point your domain or reverse proxy (Nginx / Caddy with SSL) to port `8000`, and set `VITE_API_URL` in Vercel to your domain.

---

## 4. Verification Checklist

1. [ ] Frontend builds cleanly with `npm --prefix frontend run build`.
2. [ ] Vercel project has `VITE_API_URL` set to the live backend URL.
3. [ ] Backend is running and `/` or `/api/reset` returns HTTP 200:
   ```bash
   curl -X POST https://<your-backend-url>/api/reset -H "Content-Type: application/json" -d '{"thread_id":"test"}'
   ```
4. [ ] Open the Vercel URL in your browser.
5. [ ] Open Browser DevTools -> Network tab:
   - Type a prompt: *"Oil filter for Tata Harrier 2021"*
   - Verify POST request to `https://<your-backend-url>/api/chat/start` succeeds.
   - Verify SSE stream connection to `https://<your-backend-url>/api/session/.../events` receives real-time updates.
