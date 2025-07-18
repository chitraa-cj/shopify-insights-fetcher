# Setup Guide for Shopify Store Insights Fetcher

## Quick Start

### Prerequisites
- Python 3.8 or higher
- PostgreSQL database
- Gemini API key (optional, for AI features)

### 1. Environment Setup

```bash
# Clone or access the project directory
cd shopify-insights-fetcher

# Install dependencies (automatically handled in Replit)
# Dependencies include: fastapi, uvicorn, requests, beautifulsoup4, 
# trafilatura, google-genai, asyncpg, pydantic
```

### 2. Database Configuration

The system uses PostgreSQL for data persistence:

```bash
# Database is automatically configured in Replit environment
# Connection details are available in environment variables:
# - DATABASE_URL
# - PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE
```

### 3. AI Configuration (Optional)

For enhanced intelligent content extraction:

```bash
# Set your Gemini API key in environment variables
# In Replit: Go to Secrets tab and add GEMINI_API_KEY
# The system works without this key but with reduced AI capabilities
```

### 4. Start the Application

```bash
# Run the FastAPI server
python main.py

# Or using the configured workflow:
# The server will start on http://0.0.0.0:5000
```

## Features Overview

### Core Capabilities

1. **Product Extraction**: Comprehensive product catalog analysis
2. **Brand Context**: Company information and brand story extraction
3. **Policy Extraction**: Privacy policies, terms of service, return policies
4. **FAQ Extraction**: Intelligent discovery of FAQ sections
5. **Social Media**: Social handle identification and validation
6. **Contact Information**: Email and phone number extraction
7. **Competitor Analysis**: Related store discovery and analysis
8. **Currency Detection**: Automatic currency identification with conversion
9. **Database Persistence**: Full data storage and retrieval

### AI-Powered Enhancements

When Gemini API key is provided:

1. **Intelligent Policy Discovery**: AI analyzes site structure to find hidden policies
2. **Complex FAQ Navigation**: Handles expandable sections and categorized help centers
3. **Content Enhancement**: Cleans and organizes extracted content
4. **Link Analysis**: Uses context to determine relevant content
5. **Validation & Quality Assurance**: Ensures content accuracy and completeness

## API Usage

### Basic Extraction

```bash
# Extract insights from a Shopify store
curl -X POST "http://localhost:5000/extract-insights" \
  -H "Content-Type: application/json" \
  -d '{"website_url": "https://example-store.myshopify.com"}'
```

### Health Monitoring

```bash
# Basic health check
curl http://localhost:5000/health

# Comprehensive health check (includes AI service status)
curl http://localhost:5000/health/comprehensive
```

## Configuration Options

### Environment Variables

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `DATABASE_URL` | Yes | PostgreSQL connection string | - |
| `GEMINI_API_KEY` | No | Enables AI features | None |
| `PGHOST` | Yes | Database host | - |
| `PGPORT` | Yes | Database port | - |
| `PGUSER` | Yes | Database user | - |
| `PGPASSWORD` | Yes | Database password | - |
| `PGDATABASE` | Yes | Database name | - |

### System Defaults

The application includes sensible defaults for:
- Request timeouts (30 seconds)
- Retry attempts (3 retries with exponential backoff)
- Rate limiting (10 requests per minute)
- Content limits (3000 characters for policies, 20 FAQs max)

## Architecture Overview

### SOLID Design Implementation

The system follows SOLID principles:

1. **Single Responsibility**: Each service has one clear purpose
2. **Open/Closed**: Easy to extend without modifying existing code
3. **Liskov Substitution**: All implementations work with their interfaces
4. **Interface Segregation**: Focused, specific interfaces
5. **Dependency Inversion**: Dependencies on abstractions, not concrete classes

### Key Components

```
├── main.py                 # FastAPI application entry point
├── models.py              # Pydantic data models
├── services/              # Core business logic
│   ├── scraper.py         # Main orchestration service
│   ├── product_scraper.py # Product extraction
│   ├── content_scraper.py # Policy and FAQ extraction
│   ├── social_scraper.py  # Social media discovery
│   ├── ai_validator.py    # AI validation and enhancement
│   ├── database_service.py # Data persistence
│   ├── intelligent_content_extractor.py # AI-powered extraction
│   ├── base.py            # Base classes and interfaces
│   ├── interfaces.py      # Service interfaces
│   ├── factory.py         # Service creation patterns
│   └── health_checker.py  # System health monitoring
├── static/               # Web interface
│   ├── index.html        # Main web interface
│   ├── script.js         # Frontend JavaScript
│   └── style.css         # Styling
└── utils/               # Helper utilities
    └── helpers.py       # Common utility functions
```

## Testing & Validation

### Quick Test

```bash
# Test with a known Shopify store
curl -X POST "http://localhost:5000/extract-insights" \
  -H "Content-Type: application/json" \
  -d '{"website_url": "https://memy.co.in"}' | jq '.brand_insights.products | length'
```

### Edge Case Testing

```bash
# Run comprehensive edge case tests
python test_edge_cases.py --quick --url http://localhost:5000
```

### Health Validation

```bash
# Check all system components
curl -s http://localhost:5000/health/comprehensive | jq '.services'
```

## Common Issues & Solutions

### 1. AI Features Not Working

**Problem**: Policy and FAQ extraction not finding content

**Solutions**:
- Verify GEMINI_API_KEY is set in environment variables
- Check API quota limits in Google Cloud Console
- Review logs for specific AI errors
- System continues with traditional extraction as fallback

### 2. Database Connection Issues

**Problem**: Cannot save extracted data

**Solutions**:
- Verify DATABASE_URL is correct
- Check PostgreSQL service is running
- Ensure database user has write permissions
- Review connection logs for specific errors

### 3. Slow Extraction Performance

**Problem**: Long response times for complex sites

**Solutions**:
- AI-enhanced extraction may take longer (30-60 seconds for complex sites)
- Check network connectivity to target sites
- Monitor rate limiting and adjust if necessary
- Use health checks to verify system performance

### 4. Empty Results

**Problem**: No data extracted from valid Shopify stores

**Solutions**:
- Verify the URL is a valid Shopify store
- Check if the store has public product data
- Review logs for specific extraction errors
- Some stores may block automated access

## Performance Characteristics

### Typical Response Times
- **Simple stores**: 10-20 seconds
- **Complex stores (with AI)**: 30-60 seconds
- **Health checks**: < 5 seconds
- **Database operations**: < 2 seconds

### Resource Usage
- **Memory**: ~200-500MB during extraction
- **CPU**: Moderate during AI processing
- **Network**: Efficient with connection pooling
- **Database**: Minimal storage footprint

## Advanced Configuration

### Custom AI Prompts

The system allows customization of AI prompts for specific extraction needs. Modify the intelligent content extractors in `services/intelligent_content_extractor.py`.

### Extended Timeout Settings

For very large stores or slow networks:

```python
# Modify in services/base.py
DEFAULT_TIMEOUT = 60  # Increase from 30 seconds
MAX_RETRIES = 5       # Increase from 3 retries
```

### Database Schema Customization

The system automatically creates necessary tables. For custom schema modifications, update `models.py` and `services/database_service.py`.

## Monitoring & Maintenance

### Log Monitoring

Key log messages to monitor:
```
INFO: Successfully extracted insights for [URL]
WARNING: AI extraction failed, falling back to traditional method
ERROR: Database connection failed
INFO: Intelligent policy extraction found X policy types
```

### Performance Metrics

The system tracks:
- Extraction success rates
- AI service response times
- Database operation performance
- Network request efficiency
- Error rates by service component

### Regular Maintenance

1. **Monitor API quotas** for Gemini usage
2. **Database cleanup** for old extraction records
3. **Log rotation** to manage disk space
4. **Health check monitoring** for service availability
5. **Performance tuning** based on usage patterns

This setup guide provides everything needed to deploy and operate the Shopify Store Insights Fetcher with full AI-powered content extraction capabilities.