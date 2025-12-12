# 💱 Smart Currency Insight: AI-Powered Exchange Rate Analyzer

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Backend-Flask-green.svg)](https://flask.palletsprojects.com/)
[![Gemini](https://img.shields.io/badge/AI-Gemini%202.5%20Pro-orange.svg)](https://deepmind.google/technologies/gemini/)
[![Google Maps](https://img.shields.io/badge/API-Google%20Maps-red.svg)](https://developers.google.com/maps)
[![License](https://img.shields.io/badge/License-MIT-lightgrey.svg)]()

**Smart Currency Insight** is a comprehensive financial tool that goes beyond simple exchange rate tracking. It combines real-time data scraping, location-based services, and Generative AI to provide users with actionable financial intelligence.

This application doesn't just tell you *what* the exchange rate is; it tells you *where* to get the best deal nearby and uses AI to analyze *why* the market is moving.

---

## 🚀 Key Features (核心功能)

### 🤖 1. AI-Driven Market Analysis (Gemini 2.5 Pro)
- **Trend Forecasting:** Integrates Google Gemini 2.5 Pro to analyze historical data and recent financial news.
- **Actionable Insights:** Generates professional, bullet-point summaries explaining *why* a currency is fluctuating and predicting its future trend (Bullish/Bearish/Neutral).
- **RAG-like Architecture:** Feeds real-time scraped news snippets and historical rates into the LLM context window for grounded analysis.

### 📍 2. Geo-Intelligent "Best Rate" Locator
- **Smart Ranking:** Scrapes real-time exchange rates from major banks and identifies the top 3 banks with the best "Cash Sell" rates.
- **LBS Integration:** Uses the **Google Maps Places API** to find the nearest physical branches of those top-ranking banks relative to the user's current location.
- **Operational Status:** Displays real-time open/closed status, Google ratings, and navigation links.

### 📊 3. Dynamic Data Visualization & Calculator
- **Interactive Charts:** Renders historical exchange rate trends using **Chart.js** with customizable date ranges (3 months, 6 months, or custom).
- **Real-time Conversion:** Instant TWD to Foreign Currency calculator based on the currently best-available market rate.
- **Robust Scraping:** Implements a resilient scraping engine (`BeautifulSoup`) capable of parsing complex banking tables from "FindRate" and "Bank of Taiwan".

---

## 🏗️ System Architecture

The application follows a **Service-Oriented Architecture (SOA)** with a clean separation between the frontend presentation, backend logic, and external API integrations.

graph TD
    User[User Interface (HTML/JS)] -->|REST API| Flask[Flask Backend]
    
    subgraph "Data Acquisition Layer"
        Flask -->|Scrape| FindRate[FindRate Website]
        Flask -->|Scrape| BOT[Bank of Taiwan]
        Flask -->|Search| GoogleSearch[Google Custom Search API]
    end
    
    subgraph "Intelligence Layer"
        Flask -->|Context + Prompt| Gemini[Gemini 2.5 Pro Model]
        Flask -->|Geo-Query| Maps[Google Maps Places API]
    end
    
    FindRate -->|Raw HTML| Parser[BeautifulSoup Parser]
    BOT -->|Historical Data| Parser
    
    Parser -->|Structured Data| Flask
    GoogleSearch -->|News Snippets| Flask
    
    Gemini -->|Analysis Text| Flask
    Maps -->|Location Data| Flask
    
    Flask -->|JSON Response| User

🛠️ Tech Stack
Backend: Python, Flask, Waitress (Production WSGI)

Frontend: HTML5, CSS3 (Dark Mode), Vanilla JavaScript, Chart.js

AI & ML: Google Vertex AI (Gemini 2.5 Pro)

External APIs:

Google Maps Places API (Location Services)

Google Custom Search JSON API (Financial News)

Data Engineering: BeautifulSoup4 (Web Scraping), Requests

⚡ Quick Start
Prerequisites
Python 3.10+

Google Cloud Project with the following APIs enabled:

Vertex AI API

Maps JavaScript API / Places API

Custom Search API

Installation
Clone the repository

Bash

git clone [https://github.com/your-username/smart-currency-insight.git](https://github.com/your-username/smart-currency-insight.git)
cd smart-currency-insight
Install dependencies

Bash

pip install -r requirements.txt
Configuration

Place your Google Service Account JSON key in the root directory.

Update config.json:

JSON

{
  "Maps_api_key": "YOUR_GOOGLE_MAPS_API_KEY",
  "Google_search_ENGINE_ID": "YOUR_SEARCH_ENGINE_ID"
}
Run the Application

Bash

python app.py
Access the dashboard at http://localhost:5000 (or http://127.0.0.1:8000 for production mode).

📂 Project Structure
Plaintext

smart-currency-insight/
├── agent/                  # (Optional) Future agentic capabilities
├── static/
│   ├── css/style.css       # Modern Dark UI Styling
│   └── js/main.js          # Frontend Logic & Charting
├── templates/
│   └── index.html          # Main Dashboard
├── app.py                  # Flask Application Entry Point
├── rate_scraper.py         # Core Scraping Logic (ETL)
├── gemini_analyzer.py      # LLM Integration Module
├── config.json             # API Configuration
└── requirements.txt        # Dependency List
🔮 Future Roadmap
[ ] Automated Alerts: Email/Line notifications when rates hit a target low.

[ ] Multi-Model Support: Integration with OpenAI GPT-4 for comparative analysis.

[ ] Mobile App: React Native wrapper for mobile deployment.
