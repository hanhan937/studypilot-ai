# StudyPilot AI

A full-stack AI study agent, built one module at a time.

**Current status: Module 1 – Project Setup & Architecture.**
There is no AI agent, OpenAI connection, PostgreSQL or authentication yet.

## Tech stack

| Part     | Technology                                   |
| -------- | -------------------------------------------- |
| Frontend | React + TypeScript + Vite + Tailwind CSS 3   |
| Backend  | Python + Django + Django REST Framework      |
| Later    | OpenAI Agents SDK, PostgreSQL, Docker        |

## Project structure

```
studypilot-ai/
├── backend/                 Django project
│   ├── manage.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── config/              Project settings and root URLs
│   └── api/                 App holding API endpoints (GET /api/health/)
├── frontend/                React app
│   ├── package.json
│   ├── .env.example
│   ├── index.html
│   └── src/                 main.tsx, App.tsx, index.css
├── .gitignore
└── README.md
```

## Prerequisites

- Python 3.10+ (3.12 recommended)
- Node.js 18+ (20 or newer recommended) and npm

## Run the backend (terminal 1)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # Windows: copy .env.example .env
# Open .env and set DJANGO_SECRET_KEY to your own random string.
# You can generate one with:
#   python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"

python manage.py check
python manage.py runserver       # http://localhost:8000
```

Test it:

```bash
curl http://localhost:8000/api/health/
# {"status":"ok","message":"StudyPilot API is running"}
```

Run the backend test:

```bash
python manage.py test
```

## Run the frontend (terminal 2)

```bash
cd frontend
npm install
npm run dev                      # http://localhost:5173
```

Open http://localhost:5173 and click **Check API Health**.
The page shows the API response, or an error message if the backend is not running.

To point the frontend at a different backend address, copy `frontend/.env.example`
to `frontend/.env` and change `VITE_API_BASE_URL`.

Production build check:

```bash
npm run build
```

## How the frontend talks to the backend

The browser at `http://localhost:5173` calls `http://localhost:8000/api/health/` with `fetch`.
These are different origins, so Django must allow it. `django-cors-headers` does this, using the
origins listed in `CORS_ALLOWED_ORIGINS` (backend `.env`).

## Troubleshooting

- **`DJANGO_SECRET_KEY is not set`** – you forgot `cp .env.example .env` in `backend/`.
- **Frontend shows "Could not reach the backend"** – start Django first, and check that the port
  matches `VITE_API_BASE_URL`.
- **Browser console shows a CORS error** – make sure your frontend address is in
  `CORS_ALLOWED_ORIGINS`, then restart Django.
