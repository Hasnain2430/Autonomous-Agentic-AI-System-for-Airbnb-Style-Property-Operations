# Autonomous Airbnb Property Operations Manager

A multi-agent system that autonomously manages digital operations for up to 3 Airbnb-style properties. The system handles guest interactions, bookings, payments, cleaning coordination, issue resolution, and calendar management.

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- Docker (for n8n, if using Docker)
- Telegram account (for bot creation)
- Google account (for Calendar API)

### Installation

1. **Clone the repository** (if applicable) or navigate to project directory

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   ```

3. **Activate virtual environment:**
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your actual values
   ```

6. **Run the application:**
   ```bash
   uvicorn api.main:app --reload
   ```

## 📁 Project Structure

```
Project/
├── agents/              # Agent implementations
├── api/                  # FastAPI application
│   ├── routes/          # API routes
│   ├── models/          # Pydantic models
│   ├── utils/           # Utility functions
│   └── telegram/        # Telegram bot handlers
├── database/            # Database models and setup
├── config/              # Configuration management
├── storage/             # File storage
│   ├── photos/          # Property photos
│   └── payment_screenshots/  # Payment screenshots
├── n8n_workflows/       # n8n workflow exports
├── tests/               # Test scripts
└── docs/                # Documentation
```

## 🤖 Agents

1. **Inquiry & Booking Agent** - Handles guest inquiries and booking process
2. **Issue Handling Agent** - Manages guest issues during stays
3. **Cleaner Coordination Agent** - Schedules and coordinates cleaning tasks
4. **Host Summary Agent** - Generates weekly and monthly reports

## 📚 Documentation

- [Project Description](docs/project%20Description.md)
- [Implementation Plan](docs/plan.md)
- [Implementation Status](docs/implementation-status.md)
- [Project Summary](docs/project-summary.md)

## 🔧 Configuration

See [Implementation Plan](docs/plan.md) for detailed setup instructions.

## 📝 License

This project is for educational purposes.

