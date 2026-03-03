# SWELL Backend

This is the backend service for the SWELL fashion recommendation platform. It provides RESTful APIs for user authentication, personalized outfit recommendations, virtual fitting room logic, and user closet management. The backend integrates with machine learning models and LLMs to power its sophisticated recommendation algorithms.

## Project Overview

**SWELL Backend** handles the core business logic, data persistence, and recommendation engine integration for the platform.

**Technology Stack:**
- **Framework:** FastAPI (Python 3.11)
- **Database:** PostgreSQL with `pgvector` extension for vector embeddings (version control by Alembic)
- **ORM:** SQLAlchemy (Async)
- **Authentication:** JWT (JSON Web Tokens)
- **Machine Learning Integration:** PyTorch (NeuMF, BPR), CLIP for Fashion Item Embedding
- **LLM Integration:** Google Gemini API
- **Cloud Storage:** AWS S3

## Getting Started

### Prerequisites

- Python 3.11
- PostgreSQL database (with `pgvector` extension installed)
- Google Gemini API Key
- AWS S3 Credentials

### Installation

1. **Create and activate a virtual environment:**
   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate  # On macOS/Linux
   # or
   .venv\Scripts\activate     # On Windows
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Configuration:**
   Copy the example environment file and configure your credentials.
   ```bash
   cp .env.example .env
   ```
   *Make sure to configure `DATABASE_URL`, `GOOGLE_API_KEY`, and AWS S3 credentials in `.env`.*

### Running the Development Server

Start the FastAPI application with uvicorn:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`.
You can access the interactive API documentation (Swagger UI) at `http://localhost:8000/docs`.

## Project Structure

```text
backend/
├── app/                      # Core application code
│   ├── api/                  # API routers and endpoints
│   ├── core/                 # Core configuration, security, and settings (JWT, etc.)
│   ├── db/                   # Database session management and engine configuration
│   ├── models/               # SQLAlchemy database models
│   ├── schemas/              # Pydantic schemas for request/response validation
│   └── services/             # Business logic (auth, recommendations, LLM, etc.)
├── data/                     # Data and Recommendation Engine pipelines (moved to root level logic)
├── scripts/                  # Utility scripts for database population and maintenance
├── main.py                   # FastAPI application entry point
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variables template
└── README.md                 # This file
```

## Core Features & API Modules

### Authentication (`/api/auth`)
- User Registration and Login via JWT.
- Secure password hashing using bcrypt.
- Token generation and verification Middleware.

### Onboarding & Preferences (`/api/onboarding`)
- Endpoint to fetch preference tags.
- Cold-start mechanism fetching initial sample outfits.
- Register user style profiles to calibrate initial recommendations.

### Recommendations (`/api/outfits`)
- Serves personalized outfit feeds.
- Handled by a sophisticated hybrid recommendation pipeline combining Deep Learning (Night Model) and real-time interaction updates (Day Model).
- Like/Skip endpoints to update user preference vectors dynamically.

### Closet & Virtual Fitting (`/api/closet` & `/api/virtual-fitting`)
- User personal closet management.
- Trigger virtual fitting background tasks leveraging multimodal AI.

### Machine Learning Integration
- **LLM Contextualization:** Generates descriptive reasons and style advice for recommended outfits using the Gemini API (`app/services/llm_service.py`).
- **Vector Search:** Utilizes PostgreSQL `pgvector` to perform similarity searches based on calculated image and text embeddings.

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [PostgreSQL pgvector](https://github.com/pgvector/pgvector)
