# CityScope (React + FastAPI)

CityScope is a location-aware routing and urban incident analytics demo for NYC.

- **Frontend:** React + Vite + Leaflet
- **Backend:** FastAPI reusing existing Python data/risk/routing modules
- **Routing:** OpenRouteService
- **Data:** NYC Open Data (311, NYPD, restaurant inspections)

## Project Structure

- `backend/` - FastAPI app and service layer
- `frontend/` - React UI (Navigation + Analytics tabs)
- `data/`, `models/`, `routing/`, `utils/` - shared Python logic

## Prerequisites

- Python 3.10+
- Node.js 18+ and npm

## Backend Setup

1. Install Python dependencies:

```bash
pip install -r requirements.txt
```

2. Create `backend/.env`:

```bash
touch backend/.env
```

On Windows PowerShell:

```powershell
New-Item -Path backend/.env -ItemType File
```

3. Set secrets in `backend/.env`:

```env
OPENROUTESERVICE_API_KEY=your_openrouteservice_key
NYC_OPEN_DATA_TOKEN=your_nyc_open_data_token
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.0-flash
```

4. Run backend:

```bash
uvicorn backend.main:app --reload --port 8000
```

## Frontend Setup

1. Install frontend dependencies:

```bash
cd frontend
npm install
```

2. Create frontend env file:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

3. Confirm API URL in `frontend/.env`:

```env
VITE_API_BASE_URL=http://localhost:8000
```

4. Run frontend:

```bash
npm run dev
```

Open `http://localhost:5173`.

## Demo Validation Checklist

### Navigation tab

- Type in origin and destination fields.
- Verify inline autocomplete suggestions appear directly under each input.
- Select suggestions and verify text input is replaced with selected address.
- Click **Compute Routes** and verify:
  - map renders recommended + alternative routes
  - route cards show ETA, distance, and risk metrics

### Analytics tab

- Confirm summary cards load.
- Confirm trend chart renders for the selected day window.
- Confirm hotspot map renders points.

## API Endpoints

- `GET /health`
- `GET /geocode/suggest?q=...`
- `POST /navigation/compute`
- `GET /analytics/summary?days=...`
- `GET /analytics/trends?days=...`
- `GET /analytics/hotspots?days=...`

## Notes

- Use neutral language in UI: higher incident density, not certainty of outcomes.
- Reported incidents are not complete ground truth and may include reporting/geocoding bias.