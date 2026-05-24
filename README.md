# Poultry Market Intel

AI-powered intelligence platform for tracking fertilized egg and day-old chick prices,
analyzing market trends over 3 years, detecting seasonal effects, and predicting future prices.

## Architecture

```
poultry-market-intel/
├── backend/          # FastAPI + PostgreSQL (async)
│   ├── app/
│   │   ├── api/          # REST endpoints
│   │   ├── core/         # Config & settings
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── schemas/      # Pydantic request/response schemas
│   │   ├── services/     # Business logic
│   │   └── db/           # Database session & connection
│   ├── alembic/          # Database migrations
│   └── tests/
├── web/              # Next.js + Tailwind dashboard
│   ├── src/
│   │   ├── app/          # Pages & layouts
│   │   ├── components/   # Shared UI components
│   │   ├── lib/          # API client & utilities
│   │   └── styles/       # Global CSS
│   └── __tests__/
├── mobile/           # Flutter mobile app
│   ├── lib/
│   └── test/
├── ai-engine/        # Python Pandas + Prophet forecasting
│   ├── src/
│   │   ├── data_loader.py
│   │   ├── forecast.py
│   │   ├── seasonal.py
│   │   └── main.py
│   ├── models/          # Trained model artifacts
│   ├── data/            # Historical data exports
│   └── tests/
├── docker/           # Dev & prod Docker compose files
├── scripts/          # Utility scripts
└── .github/workflows # CI/CD pipelines
```

## Features

- **Fertilized Egg Price Tracking** — monitor prices per 1000 eggs across regions
- **Day-Old Chick (DOC) Price Tracking** — track DOC pricing trends
- **3-Year Trend Comparison** — overlay year-over-year price movements
- **Seasonal Effect Detection** — identify impacts from winter, Ramadan, Eid, Sham El-Nessim, Christian holidays
- **AI Price Prediction** — Meta Prophet forecasts with confidence intervals

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.12+ (for local backend/AI dev)
- Node.js 20+ (for local web dev)
- Flutter SDK (for mobile dev)

### Docker (full stack)

```bash
docker compose up --build
```

- Backend API: http://localhost:8000
- Web Dashboard: http://localhost:3000
- API Docs (Swagger): http://localhost:8000/docs

### Local Development

**Backend:**

```bash
cd backend
python -m venv venv
.\venv\Scripts\activate    # Windows
# source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

**Web:**

```bash
cd web
npm install
cp .env.example .env.local
npm run dev
```

**AI Engine:**

```bash
cd ai-engine
python -m venv venv
pip install -r requirements.txt
python -m src.main forecast --product fertilized_eggs
python -m src.main seasonal --product fertilized_eggs
```

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | Async PostgreSQL connection string | `postgresql+asyncpg://poultry:poultry@localhost:5432/poultry_market` |
| `DATABASE_SYNC_URL` | Sync PostgreSQL connection string | `postgresql+psycopg2://poultry:poultry@localhost:5432/poultry_market` |
| `DEBUG` | Enable debug mode | `true` |
| `NEXT_PUBLIC_API_URL` | Backend API URL for web app | `http://localhost:8000/api/v1` |

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/api/v1/prices/` | List price records (filterable) |
| `POST` | `/api/v1/prices/` | Create price record |
| `GET` | `/api/v1/predictions/` | List predictions (filterable) |

Full API docs available at `/docs` (Swagger UI) or `/redoc` (ReDoc).

## Seasonal Calendar

The platform accounts for these seasonal events:

- **Winter** (Dec–Feb): Higher poultry demand
- **Ramadan** (variable): Pre-Ramadan price spikes
- **Eid al-Fitr / Eid al-Adha**: Post-festival demand shifts
- **Sham El-Nessim** (Spring): Traditional egg consumption
- **Christian holidays** (Christmas, Easter): Demand variations

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI (Python) |
| Database | PostgreSQL 16 |
| Web Dashboard | Next.js 14 + Tailwind CSS |
| Mobile App | Flutter |
| AI/ML Engine | Python, Pandas, Prophet |
| Containerization | Docker & Docker Compose |
| ORM | SQLAlchemy 2.0 (async) |
| Migrations | Alembic |
