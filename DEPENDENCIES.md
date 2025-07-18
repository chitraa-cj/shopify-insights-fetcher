# Project Dependencies

This document lists all the required dependencies for the Shopify Store Insights Fetcher application.

## Core Dependencies

### Web Framework
- **fastapi==0.104.1** - Modern Python web framework for building APIs
- **uvicorn[standard]==0.24.0** - ASGI server for running FastAPI applications

### Data Validation
- **pydantic==2.5.0** - Data validation and serialization using Python type annotations

### Web Scraping
- **requests==2.31.0** - HTTP library for making web requests
- **beautifulsoup4==4.12.2** - HTML/XML parsing library
- **trafilatura==1.6.4** - Text extraction from web pages

### Database
- **asyncpg==0.29.0** - PostgreSQL adapter for Python

### Utilities
- **python-multipart==0.0.6** - For handling multipart form data

## Optional Dependencies

### AI Features (Requires API Key)
- **google-genai==0.8.0** - Google Gemini AI client library
  - **Note**: Requires `GEMINI_API_KEY` environment variable
  - **Without this key**: AI validation features will be disabled, but all other functionality works normally

## Installation

All dependencies are already installed in this Replit environment. If running elsewhere:

```bash
pip install fastapi uvicorn[standard] pydantic requests beautifulsoup4 trafilatura asyncpg python-multipart google-genai
```

## Environment Variables Required

### Essential
- `DATABASE_URL` - PostgreSQL connection string (automatically provided in Replit)

### Optional
- `GEMINI_API_KEY` - Google Gemini API key for AI validation features
  - If not provided, the application will run without AI features
  - Get your key from: https://aistudio.google.com/app/apikey

## Features Available Without API Key

When `GEMINI_API_KEY` is not provided, the following features still work:

✅ **Product Extraction** - Full product catalog and hero products
✅ **Currency Detection & Conversion** - Automatic price conversion
✅ **FAQ Extraction** - Basic FAQ scraping from HTML
✅ **Policy Extraction** - Policy links and content extraction
✅ **Social Media Detection** - Social handles extraction
✅ **Contact Information** - Email, phone, and address extraction
✅ **Competitor Analysis** - Similar store discovery
✅ **Database Persistence** - All data saved to PostgreSQL
✅ **Web Interface** - Complete frontend functionality

## Features Requiring API Key

❌ **AI Content Validation** - Quality assessment of extracted content
❌ **Intelligent Content Improvement** - AI-powered content enhancement
❌ **Advanced FAQ Filtering** - AI-based navigation menu removal
❌ **Smart Policy Content Analysis** - AI validation of policy completeness
❌ **Comprehensive Quality Scoring** - Overall extraction quality assessment