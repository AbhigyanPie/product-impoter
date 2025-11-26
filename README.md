# Product Importer

A scalable web application for importing products from CSV files into a SQL database. Built with FastAPI, SQLAlchemy, and Celery, featuring real-time progress tracking and a clean, elegant user interface.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Running the Application](#running-the-application)
- [API Reference](#api-reference)
- [CSV Format](#csv-format)
- [Deployment](#deployment)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Performance](#performance)
- [License](#license)

---

## Features

- **Large CSV Import**: Upload and process CSV files containing up to 500,000 products
- **Real-Time Progress**: Server-Sent Events (SSE) provide live progress updates during import
- **Product Management**: Full CRUD operations with search, filtering, and pagination
- **Bulk Operations**: Delete all products with confirmation safeguard
- **Webhook System**: Configure webhooks to receive notifications on product events
- **Case-Insensitive SKU**: Automatic SKU normalization prevents duplicates
- **Upsert Logic**: Existing products are updated based on SKU match
- **Responsive UI**: Clean interface that works on desktop and mobile devices

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend Framework | FastAPI (Python) |
| Database | SQLite (development) / PostgreSQL (production) |
| ORM | SQLAlchemy 2.0 |
| Task Queue | Celery with Redis (optional) |
| Frontend | Vanilla HTML, CSS, JavaScript |
| Real-Time Updates | Server-Sent Events (SSE) |
| HTTP Client | HTTPX |

---

## Architecture

### Local Development

```
Browser --> FastAPI --> SQLite
               |
               v
         Background Thread (CSV Processing)
               |
               v
         In-Memory Progress Store
```

### Production Environment

```
Browser --> FastAPI --> PostgreSQL
               |
               v
            Redis
               |
               v
         Celery Worker (CSV Processing)
```

The application automatically detects available services and adapts accordingly:

- No DATABASE_URL environment variable: Uses SQLite
- No Redis connection: Uses in-memory storage and threading
- DATABASE_URL provided: Uses PostgreSQL
- Redis available: Uses Celery for background tasks

---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)

For production deployment:
- PostgreSQL 13+
- Redis 6+

### Installation

1. Clone the repository

```bash
git clone https://github.com/yourusername/product-importer.git
cd product-importer
```

2. Create and activate a virtual environment

```bash
# Linux/macOS
python -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
.\venv\Scripts\Activate
```

3. Install dependencies

```bash
pip install -r requirements.txt
```

### Running the Application

Start the development server:

```bash
uvicorn app.main:app --reload --port 8000
```

The application will be available at `http://localhost:8000`

Expected output:

```
==================================================
  Product Importer
==================================================
  Database: SQLite (local)
  Tables: Created/Verified
==================================================

INFO:     Uvicorn running on http://127.0.0.1:8000
```

---

## API Reference

### Products

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/products | List products with pagination and filtering |
| GET | /api/products/{id} | Get a single product by ID |
| POST | /api/products | Create a new product |
| PUT | /api/products/{id} | Update an existing product |
| DELETE | /api/products/{id} | Delete a product |
| DELETE | /api/products?confirm=true | Delete all products |

#### Query Parameters for GET /api/products

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| page | integer | 1 | Page number |
| page_size | integer | 20 | Items per page (max 100) |
| search | string | null | Search in SKU, name, description |
| active | boolean | null | Filter by active status |

### Uploads

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/uploads | Upload a CSV file for processing |
| GET | /api/uploads/{task_id} | Get upload task status |
| GET | /api/uploads/{task_id}/stream | Stream progress via SSE |

### Webhooks

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/webhooks | List all webhooks |
| GET | /api/webhooks/events | List available event types |
| GET | /api/webhooks/{id} | Get a single webhook |
| POST | /api/webhooks | Create a new webhook |
| PUT | /api/webhooks/{id} | Update a webhook |
| DELETE | /api/webhooks/{id} | Delete a webhook |
| POST | /api/webhooks/{id}/test | Test a webhook |

#### Available Webhook Events

- product.created
- product.updated
- product.deleted
- bulk.imported
- bulk.deleted

---

## CSV Format

The CSV file should contain the following columns:

| Column | Required | Type | Description |
|--------|----------|------|-------------|
| sku | Yes | string | Unique product identifier (case-insensitive) |
| name | Yes | string | Product name |
| description | No | string | Product description |
| price | No | decimal | Product price |
| quantity | No | integer | Stock quantity |

### Example CSV

```csv
sku,name,description,price,quantity
PROD-001,Widget A,High-quality widget,29.99,100
PROD-002,Widget B,Economy widget,19.99,250
PROD-003,Gadget X,Premium gadget,149.99,50
```

### Import Behavior

- SKU values are normalized to lowercase
- Duplicate SKUs update existing records (upsert)
- Missing optional fields default to: description=null, price=0.0, quantity=0
- All imported products are set to active=true

---

## Deployment

### Deploy to Render

1. Push your code to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/yourusername/product-importer.git
git branch -M main
git push -u origin main
```

2. Create a new Blueprint on Render

- Go to https://render.com
- Click "New" and select "Blueprint"
- Connect your GitHub repository
- Render will detect the render.yaml configuration

3. The blueprint creates:

- Web Service (FastAPI application)
- Background Worker (Celery)
- PostgreSQL Database
- Redis Instance

4. Wait for deployment to complete (approximately 5-10 minutes)

### Environment Variables

For production deployment, set these environment variables:

| Variable | Description | Example |
|----------|-------------|---------|
| DATABASE_URL | PostgreSQL connection string | postgresql://user:pass@host:5432/dbname |
| REDIS_URL | Redis connection string | redis://host:6379/0 |
| DEBUG | Enable debug mode | false |

### Deploy with Docker

```bash
docker-compose up --build
```

This starts all services: PostgreSQL, Redis, FastAPI, and Celery worker.

---

## Project Structure

```
product-importer/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Application settings
│   ├── database.py          # Database connection setup
│   ├── models.py            # SQLAlchemy ORM models
│   ├── schemas.py           # Pydantic validation schemas
│   ├── crud.py              # Database operations
│   ├── tasks.py             # Background task processing
│   ├── celery_app.py        # Celery configuration
│   └── routers/
│       ├── __init__.py
│       ├── products.py      # Product API endpoints
│       ├── uploads.py       # Upload API endpoints
│       └── webhooks.py      # Webhook API endpoints
├── static/
│   ├── css/
│   │   └── style.css        # Application styles
│   └── js/
│       └── app.js           # Frontend JavaScript
├── templates/
│   └── index.html           # Main HTML template
├── requirements.txt         # Python dependencies
└── README.md
```

---

## Configuration

Configuration is managed through environment variables. Create a `.env` file for local development:

```env
# Database (optional - defaults to SQLite)
DATABASE_URL=postgresql://user:password@localhost:5432/product_importer

# Redis (optional - falls back to in-memory)
REDIS_URL=redis://localhost:6379/0

# Application settings
DEBUG=true
MAX_FILE_SIZE_MB=100
CHUNK_SIZE=1000
```

### Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| DATABASE_URL | sqlite:///./products.db | Database connection string |
| REDIS_URL | redis://localhost:6379/0 | Redis connection string |
| DEBUG | true | Enable debug mode |
| MAX_FILE_SIZE_MB | 100 | Maximum upload file size in MB |
| CHUNK_SIZE | 1000 | Rows per batch during import |

---

## Performance

### Large File Processing

- Files are processed in chunks of 1000 rows (configurable)
- Progress updates are sent after each chunk
- Database operations use bulk upsert for efficiency

### Handling Platform Timeouts

Many hosting platforms enforce request timeouts (e.g., Heroku's 30-second limit). This application handles long-running operations by:

1. Accepting the upload and returning immediately with a task ID
2. Processing the file in the background (Celery worker or thread)
3. Providing progress updates via SSE or polling

### Estimated Processing Times

| Records | Approximate Time |
|---------|------------------|
| 10,000 | 10-20 seconds |
| 100,000 | 1-2 minutes |
| 500,000 | 5-10 minutes |

Times vary based on hardware, database performance, and network conditions.

---

## Troubleshooting

### Application fails to start

Ensure all dependencies are installed:

```bash
pip install -r requirements.txt
```

### Port already in use

Use a different port:

```bash
uvicorn app.main:app --reload --port 3000
```

### Database errors

Delete the SQLite database file and restart:

```bash
# Linux/macOS
rm products.db

# Windows
del products.db
```

### Progress bar not updating

- Wait 1-2 seconds for processing to begin
- Check browser console for JavaScript errors
- Verify the server is running without errors

---

## Author

Developed as a technical assessment project demonstrating:

- RESTful API design with FastAPI
- Database modeling with SQLAlchemy
- Asynchronous task processing
- Real-time updates with Server-Sent Events
- Clean, maintainable code architecture
