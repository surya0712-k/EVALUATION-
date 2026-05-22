# CareerLens

CareerLens is a developer profile evaluation platform that analyzes GitHub and LinkedIn profiles to generate structured candidate insights, activity signals, and evaluation reports.

The goal of this project was to understand how modern full-stack systems work end-to-end while building something practical around developer profiling and evaluation workflows.

---

## What it does

- Analyze GitHub profiles
- Extract repository and contribution signals
- Evaluate LinkedIn profile data
- Generate structured evaluation reports
- Save reports and users in PostgreSQL
- Support Google authentication
- Run fully inside Docker containers
- Expose analyzers through REST APIs
- Provide MCP tools for AI-assisted workflows in Cursor

---

## Tech Stack

### Frontend
- React
- TypeScript
- Vite
- TailwindCSS

### Backend
- FastAPI
- Python
- Pydantic
- Async workflows

### Database
- PostgreSQL
- SQLite fallback support

### DevOps / Infrastructure
- Docker
- Docker Compose

### AI / Tooling
- MCP (Model Context Protocol)
- Gemini API
- Apify (LinkedIn enrichment)

---

# Project Structure

```txt
frontend/
backend/
  app/
    analyzers/
    collectors/
    routes/
    scoring/
    workflows/
  tools/
docker-compose.yml
```

---

# Features

## GitHub Evaluation

The GitHub analyzer collects:
- repository statistics
- language usage
- stars/forks
- contribution activity
- commit activity signals
- repository quality indicators

It generates summarized engineering signals from public repositories.

---

## LinkedIn Evaluation

The LinkedIn analyzer supports:
- profile enrichment
- role extraction
- experience estimation
- skills parsing
- achievements extraction

Data can be fetched through:
- Apify
- JSON snapshots
- placeholder fallback mode

---

## Authentication

Supports:
- Google OAuth login
- JWT-like signed session tokens
- protected API routes
- persistent login state

Authentication flow:
1. User signs in with Google
2. Backend verifies Google credential
3. Internal signed token is generated
4. Frontend stores token locally
5. Protected APIs use bearer authentication

---

## MCP Tools

The project also exposes MCP tools for Cursor.

Available tools:
- `analyze_github_profile`
- `analyze_linkedin_profile`

These tools use the same analyzers as the backend APIs.

Example use case:
- Ask Cursor agent to analyze a GitHub profile directly from the IDE.

---

# Running Locally

## Clone the project

```bash
git clone <repo-url>
cd EVALUATION-
```

---

# Environment Variables

Create:

```txt
backend/.env
```

Example:

```env
DATABASE_URL=postgresql://postgres:password@postgres-db:5432/careerlens

AUTH_SECRET=change-this

GOOGLE_CLIENT_ID=your_google_client_id

GEMINI_API_KEY=your_key

APIFY_API_TOKEN=your_token
```

---

# Start with Docker

```bash
docker compose up --build
```

Frontend:
```txt
http://localhost:5173
```

Backend:
```txt
http://localhost:8000
```

---

# Database

PostgreSQL runs inside Docker.

To open PostgreSQL shell:

```bash
docker exec -it evaluation--postgres-db-1 psql -U postgres
```

Useful commands:

```sql
\l
\c careerlens
\dt
SELECT * FROM users;
```

---

# API Endpoints

## Analyze GitHub

```http
POST /api/analyze/github
```

Body:

```json
{
  "github_url": "https://github.com/username"
}
```

---

## Analyze LinkedIn

```http
POST /api/analyze/linkedin
```

---

## Full Evaluation

```http
POST /api/evaluate
```

---

# Docker Notes

The project uses:
- isolated backend container
- isolated PostgreSQL container
- Docker internal networking
- container port mapping
- persistent database volumes

Backend communicates with PostgreSQL using Docker service DNS:

```txt
postgres-db:5432
```

---

# Things I Learned While Building This

This project helped me deeply understand:

- React rendering lifecycle
- async programming
- FastAPI architecture
- authentication flows
- JWT/session handling
- PostgreSQL internals
- SQL injection prevention
- Docker networking
- container orchestration
- MCP architecture
- API design
- backend workflows
- service communication

# Screenshots
ui.png
image.png

---

# License

MIT