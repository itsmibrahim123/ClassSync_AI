# ClassSync AI - Project Context

## 1. Project Overview
ClassSync AI is an automated university timetabling system powered by a Genetic Algorithm (GA). It solves the complex constraint satisfaction problem of scheduling courses, teachers, and rooms while avoiding conflicts and optimizing for preferences.

The system consists of a Python-based calculation engine (`classsync_core`), a RESTful API (`classsync_api`), and a modern React frontend (`classsync-frontend`).

## 2. Tech Stack

### Backend
- **Language:** Python 3.10+
- **Framework:** FastAPI
- **ORM:** SQLAlchemy (Async/Sync)
- **Database:** PostgreSQL (Schema managed via Alembic)
- **Data Processing:** Pandas (for heavy dataset manipulation)
- **Algorithm:** Custom Genetic Algorithm (Evolutionary Computation)
- **Storage:** S3-compatible object storage (for dataset files)

### Frontend
- **Framework:** React 19
- **Build Tool:** Vite
- **Language:** TypeScript
- **Styling:** Tailwind CSS
- **UI Components:** Radix UI / shadcn/ui
- **State/Data Management:** TanStack Query (React Query) + Zustand
- **Routing:** React Router v7

## 3. Directory Structure & Key Files

```text
D:\GitHub\ClassSync_AI\
├── alembic/                  # Database migration scripts
├── classsync_agent/          # LLM Agent integration (Experimental)
│   └── llm_client.py         # Interface for LLM providers
├── classsync_api/            # FastAPI Web Server
│   ├── main.py               # Application entry point
│   ├── config.py             # Environment configuration
│   ├── database.py           # DB connection handling
│   ├── schemas.py            # Pydantic models (Request/Response types)
│   └── routers/              # API Endpoints
│       ├── datasets.py       # File upload & validation
│       ├── constraints.py    # Configuration management
│       ├── scheduler.py      # Timetable generation trigger
│       └── teachers.py       # Teacher management
├── classsync_core/           # The Scheduling Engine (Library)
│   ├── models.py             # SQLAlchemy Database Models (Tables)
│   ├── optimizer.py          # High-level Strategy (GA vs Heuristic)
│   ├── utils.py              # Time/Date utilities
│   ├── exporters/            # Logic to export schedules to Excel/CSV
│   ├── importers/            # Logic to parse uploaded Excel/CSV
│   └── scheduler/            # Genetic Algorithm Implementation
│       ├── ga_engine.py      # Main loop (Selection -> Crossover -> Mutation)
│       ├── chromosome.py     # Data structure representing a schedule
│       ├── fitness_evaluator.py # Scoring logic (Hard & Soft constraints)
│       ├── operators.py      # Crossover and Mutation logic
│       ├── repair.py         # Heuristics to fix broken schedules
│       └── validator.py      # Pre-GA validation logic
├── classsync-frontend/       # React Application
│   ├── src/
│   │   ├── components/       # Reusable UI components
│   │   ├── lib/              # Utilities & API client
│   │   │   └── api.ts        # Axios configuration & endpoints
│   │   ├── pages/            # Main views
│   │   │   ├── GenerateTimetable.tsx # Configuration & Trigger UI
│   │   │   ├── TimetableView.tsx     # Visual Grid View
│   │   │   └── Upload.tsx            # Data entry
│   │   └── types/            # TypeScript interfaces
└── tests/                    # Pytest suite
```

## 4. Inner Workings & Logic

### The Core Engine (Genetic Algorithm)
Located in `classsync_core/scheduler`, this is the heart of the application.
1.  **Initialization:** The `PopulationInitializer` creates a set of random schedules.
2.  **Representation:** A `Chromosome` represents a full timetable. It contains a list of `Gene` objects. Each `Gene` represents one scheduled session (Course + Section + Teacher + Room + Time).
3.  **Evolution Loop (`ga_engine.py`):
    *   **Selection:** Tournament selection picks the best schedules.
    *   **Crossover (`operators.py`):** Combines parts of two schedules (e.g., swapping days) to create new ones. *Note: Logic ensures locked assignments are preserved.*
    *   **Mutation:** Randomly changes a room, time, or day to explore new solutions.
    *   **Repair (`repair.py`):** Attempts to fix hard constraints (e.g., teacher double-booking) using heuristics.
4.  **Evaluation (`fitness_evaluator.py`):
    *   **Hard Constraints:** Must be 0 violations (e.g., Teacher booked twice at 9 AM).
    *   **Soft Constraints:** Scored 0-1000 (e.g., minimizing gaps, preferring mornings).
5.  **Output:** The best schedule is saved to the `Timetable` and `TimetableEntry` database tables.

### The API Flow (`classsync_api`)
1.  **Data Ingestion:** User uploads CSV/XLSX. `routers/datasets.py` validates the schema and stores the file in S3, then imports rows into the DB.
2.  **Configuration:** User sets constraints (e.g., "No classes on Friday"). Saved via `routers/constraints.py`.
3.  **Execution:** `routers/scheduler.py` receives a `GenerateRequest`. It instantiates `TimetableOptimizer`, which prepares data frames and runs the `GAEngine`.
4.  **Result:** The API returns the generation stats. The frontend then polls or fetches the created Timetable ID.

### The Frontend Logic (`classsync-frontend`)
1.  **State:** React Query handles server state (caching constraints, timetables).
2.  **Validation:** `GenerateTimetable.tsx` performs client-side validation to prevent sending conflicting hard constraints (e.g., start time > end time) before the API call.
3.  **Visualization:** `TimetableView.tsx` renders the schedule grid, calculating collision detection for UI rendering (overlapping blocks).

## 5. Script Interaction

### Running the System
1.  **Database:** PostgreSQL must be running.
2.  **Backend:** Run `uvicorn classsync_api.main:app --reload`. This starts the API server on port 8000. It connects to the DB using settings in `.env`.
3.  **Frontend:** Run `npm run dev` in the frontend directory. This starts the Vite server (usually port 5173). It proxies API requests to port 8000 via `vite.config.ts` or direct URL configuration.

### Deployment Flow
1.  **Migrations:** `alembic upgrade head` ensures the DB schema matches `models.py`.
2.  **Build:** `npm run build` compiles the React app to static files.
3.  **Serve:** The FastAPI app can serve the static frontend files, or they can be served via Nginx/Vercel while the API runs separately.

## 6. Recent Modifications (Status Log)
*   **Validation Hardening:** Added robust error handling in the frontend to prevent crashes when backend returns structured validation errors (422).
*   **Backend Logic:** Fixed time-slot generation in `optimizer.py` to respect user-defined slot durations (30/60 min) instead of hardcoded defaults.
*   **Reproducibility:** Added `random_seed` support to allow regenerating the exact same timetable.
*   **Safety:** Patched `utils.py` to handle time calculations crossing midnight without crashing.
