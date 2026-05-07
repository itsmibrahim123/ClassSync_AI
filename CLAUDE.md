# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ClassSync AI is an AI-powered university timetabling system that generates clash-free, optimized academic timetables using a genetic algorithm. It consists of a Python FastAPI backend, React TypeScript frontend, and an LLM-powered agent for natural language constraint configuration.

## Common Commands

### Backend (Python/FastAPI)
```bash
# Activate virtual environment (Windows)
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the API server
uvicorn classsync_api.main:app --reload

# Run tests
pytest
pytest tests/test_core.py -v  # Run specific test file
```

### Frontend (React/TypeScript)
```bash
cd classsync-frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Lint
npm run lint
```

## Architecture

### Three-Layer Structure

1. **classsync_api/** - FastAPI REST API layer
   - `main.py` - Application entry point, CORS config, router registration
   - `config.py` - Settings via pydantic-settings (loads from .env)
   - `database.py` - SQLAlchemy engine and session factory
   - `schemas.py` - Pydantic request/response models
   - `routers/` - API endpoints:
     - `datasets.py` - File upload, validation, and import to database
     - `scheduler.py` - Timetable generation and export endpoints
     - `constraints.py` - Constraint configuration CRUD
     - `health.py` - Health check endpoints

2. **classsync_core/** - Core scheduling engine
   - `models.py` - SQLAlchemy ORM models (Institution, Course, Teacher, Room, Section, Timetable, TimetableEntry, ConstraintConfig)
   - `optimizer.py` - Genetic algorithm timetable optimizer (TimetableOptimizer class)
   - `enhanced_placement.py` - Session placement logic with conflict resolution
   - `validators.py` - Dataset validation before import
   - `importers/` - Import CSV/XLSX data into database models
   - `exporters/` - Export timetables to XLSX, CSV, JSON formats
   - `exports.py` - BaseExporter abstract class and ExportManager
   - `constraints.py` - Constraint definitions and scoring
   - `storage.py` - S3 file storage service

3. **classsync_agent/** - LLM agent for natural language interaction (in development)
   - `llm_client.py` - OpenAI/Gemini client wrapper
   - `tools.py` - Tool definitions for agent function calling

### Data Flow

1. Users upload datasets (courses, rooms, teachers) via `/api/v1/datasets/upload`
2. Datasets are validated, stored in S3, and imported into PostgreSQL
3. Users configure constraints via `/api/v1/constraints`
4. Timetable generation (`/api/v1/scheduler/generate`) runs the genetic algorithm:
   - Loads data from database into pandas DataFrames
   - Creates sessions from courses/sections
   - Generates initial population of schedules
   - Evolves population via tournament selection, crossover, mutation
   - Saves best schedule to database as TimetableEntry records
5. Export via `/api/v1/scheduler/timetables/{id}/export?format=xlsx&view_type=master`

### Key Models (classsync_core/models.py)

- `ConstraintConfig` - Stores hard/soft/optional constraints as JSON columns
- `Timetable` - Generated timetable metadata (status, fitness score, generation time)
- `TimetableEntry` - Individual slot assignments (day, time, room, teacher, section)
- All models use `TimestampMixin` (created_at, updated_at) and `SoftDeleteMixin` (is_deleted)

### Genetic Algorithm (classsync_core/optimizer.py)

The `TimetableOptimizer` class implements:
- `generate_timetable()` - Main entry point
- `load_data_from_db()` - Converts SQLAlchemy models to DataFrames
- `create_sessions_from_courses()` - Creates session instances to schedule
- `calculate_fitness()` - Scores schedules (penalizes conflicts, gaps, edge times)
- `crossover()`, `mutate()`, `tournament_selection()` - GA operators
- `_save_to_database()` - Persists best schedule to TimetableEntry table

### Frontend (classsync-frontend/)

React 19 + TypeScript + Vite stack:
- Routing: react-router-dom
- State: zustand
- Forms: react-hook-form + zod validation
- UI: Tailwind CSS + Radix UI primitives
- HTTP: axios + @tanstack/react-query

## Configuration

Environment variables are loaded from `.env` file (see `classsync_api/config.py`):
- `DATABASE_URL` - PostgreSQL connection string
- `OPENAI_API_KEY`, `GEMINI_API_KEY` - LLM API keys
- `S3_*` - S3-compatible storage configuration

## API Prefix

All API endpoints are prefixed with `/api/v1` (configurable via `settings.api_prefix`).
