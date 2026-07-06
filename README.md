# Product Hunt Research Console

A lightweight local web application for researching Product Hunt launches, storing them locally, filtering them quickly, and annotating promising products for later follow-up.

## Features

- **Sync Launches** — Fetch today's or last 7 days' launches from Product Hunt's GraphQL API
- **Local Storage** — All data stored in SQLite on your machine (no cloud, no telemetry)
- **Browse & Search** — Full-text search across names, taglines, descriptions, and notes
- **Filter** — By topic, date range, and research status
- **Shortlist & Annotate** — Mark products as shortlisted, interesting, or follow-up with custom notes
- **CSV Export** — Export filtered results with topics, makers, notes, and URLs for external analysis
- **Settings UI** — Configure your Product Hunt token and default sync mode from the browser

## Prerequisites

- Python 3.11 or later
- A [Product Hunt Developer Token](https://www.producthunt.com/v2/oauth/applications)

## Setup

### 1. Clone the repository

```bash
git clone <repository-url>
cd Producthuntbasic
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

**Windows (PowerShell):**
```bash
.venv\Scripts\activate
```

**macOS / Linux:**
```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the application

**Windows:**
```bash
.\run.bat
```

**Or manually (all platforms):**
```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 5. Open in browser

Navigate to [http://127.0.0.1:8000](http://127.0.0.1:8000)

## Getting a Product Hunt Developer Token

1. Go to [Product Hunt Developer Dashboard](https://www.producthunt.com/v2/oauth/applications)
2. Create a new application (or use an existing one)
3. Copy your **Developer Token**
4. In the app, go to **Settings** and paste the token

## Usage

### First-time Setup

1. Open the app at `http://127.0.0.1:8000`
2. Go to **Settings** from the sidebar
3. Paste your Product Hunt developer token
4. Click **Save Changes**

### Syncing Launches

1. Go to **Dashboard**
2. Select a sync mode: "Sync Today's Launches" or "Sync Last 7 Days"
3. Click **Trigger Ingestion**
4. Products are fetched from Product Hunt and stored locally (duplicates are handled automatically)

### Browsing Launches

1. Click **Browse Launches** in the sidebar
2. Use the search bar to find products by name, tagline, description, or notes
3. Filter by topic, date range, or research status
4. Click **Annotate & Review** on any product to add notes

### Shortlisting Products

- Click the **star icon** on any product card to toggle shortlist status
- Or open the product detail page and set the status label to "Shortlisted"

### Adding Notes

1. Click **Annotate & Review** on a product
2. Write your research notes in the text area
3. Select a status label (None, Shortlisted, Interesting, Follow Up)
4. Click **Save Changes**

### Exporting to CSV

1. Go to **Browse Launches**
2. Apply any filters you want (optional)
3. Click **Export Results to CSV**
4. A CSV file is downloaded with all matching products including topics, makers, notes, and URLs

## Project Structure

```
Producthuntbasic/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI routes and application entry point
│   ├── database.py      # SQLite connection and session management
│   ├── models.py        # SQLAlchemy data models
│   ├── crud.py          # Database operations (read, write, upsert)
│   ├── config.py        # Settings management (.env + database)
│   ├── product_hunt.py  # Product Hunt GraphQL API client
│   └── templates/       # Jinja2 HTML templates
│       ├── base.html
│       ├── dashboard.html
│       ├── launches.html
│       ├── detail.html
│       └── settings.html
├── requirements.txt
├── run.bat              # Windows startup script
├── .env                 # Environment variables (token, sync mode)
├── .env.example         # Example environment file
└── prd.md               # Product Requirements Document
```

## Environment Variables

Create a `.env` file in the project root (or use the Settings UI):

```
PRODUCT_HUNT_TOKEN=your_token_here
DEFAULT_SYNC_MODE=today
```

| Variable | Description | Default |
|----------|-------------|---------|
| `PRODUCT_HUNT_TOKEN` | Your Product Hunt developer token | (empty) |
| `DEFAULT_SYNC_MODE` | `today` or `recent_7_days` | `today` |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI |
| Frontend | Jinja2 + HTMX + Tailwind CSS |
| Database | SQLite |
| ORM | SQLAlchemy |
| API Client | httpx (GraphQL) |

## License

This is a local personal tool. No license specified.
