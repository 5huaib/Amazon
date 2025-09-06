# Amazon Ride - Live Tracking System

This project consists of a ride-sharing application with real-time tracking capabilities.

## Project Structure

```
amazon-project/
├── frontend/
│   └── index.html          # Client-side web application
├── backend/
│   ├── amazon_server.py    # Main server API (Port 5002)
│   └── amazon_client.py    # Client-facing API (Port 5001)
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## Setup Instructions

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Start the main server:
   ```bash
   python backend/amazon_server.py
   ```

3. Start the client API:
   ```bash
   python backend/amazon_client.py
   ```

4. Open `frontend/index.html` in your browser

## Architecture

- **Frontend**: Single-page HTML application with real-time map tracking
- **Client API**: Acts as a proxy between frontend and main server (Port 5001)
- **Main Server**: Core business logic and database operations (Port 5002)
