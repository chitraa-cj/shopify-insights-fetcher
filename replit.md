# Shopify Store Insights Fetcher

## Overview

The Shopify Store Insights Fetcher is a Python-based web application that extracts comprehensive brand insights from Shopify stores without using the official Shopify API. The application analyzes publicly available data from Shopify stores to provide structured information about products, brand context, policies, social media handles, and contact details.

## User Preferences

Preferred communication style: Simple, everyday language.
Backend preference: Python-only implementation with AI-powered validation using Gemini.
Latest Request: Enhanced intelligent policy and FAQ extraction that automatically discovers and extracts content from privacy policies, terms of service, and segmented FAQ sections using AI reasoning for complex site navigation.

## Recent Enhancements (Latest)

- ✅ **SOLID Design Principles Implementation**: Complete refactor using object-oriented design patterns
- ✅ **Comprehensive Error Handling**: Circuit breakers, retry mechanisms, and graceful degradation
- ✅ **Interface Segregation**: Separate interfaces for each extraction capability
- ✅ **Dependency Injection**: Factory pattern for service creation with proper dependency management  
- ✅ **Optional Gemini API Key**: Application works fully without AI features when key unavailable
- ✅ **Service Registry Pattern**: Centralized service management with proper lifecycle handling
- ✅ **Parallel Extraction**: Concurrent operations with proper error isolation
- ✅ **Metrics & Monitoring**: Built-in operation tracking and performance metrics
- ✅ **Health Checks**: Comprehensive service health monitoring and dependency validation
- ✅ **Rate Limiting**: Intelligent request throttling to prevent service overload
- ✅ **URL Validation**: Robust URL parsing and normalization with edge case handling
- ✅ **Intelligent Content Extraction**: AI-powered policy and FAQ extraction using Gemini reasoning
- ✅ **Complex Site Navigation**: Automatically discovers content in expandable sections and help centers
- ✅ **AI Reasoning for Content Discovery**: Uses LLM to intelligently navigate complex site structures like ColourPop's segmented FAQ sections

## System Architecture

The application follows SOLID design principles with a comprehensive object-oriented architecture:

### Design Patterns Implemented:
- **Factory Pattern**: Service and extractor creation with dependency injection
- **Adapter Pattern**: Backward compatibility with legacy API
- **Observer Pattern**: Metrics collection and monitoring
- **Circuit Breaker Pattern**: Prevents cascading failures
- **Registry Pattern**: Centralized service management
- **Strategy Pattern**: Multiple extraction strategies with fallbacks

### Core Architecture Components:

1. **Web Framework**: FastAPI for high-performance API endpoints
2. **Scraping Engine**: Multi-service scraper architecture with specialized scrapers
3. **Data Models**: Pydantic models for type safety and validation
4. **Frontend**: Static HTML/CSS/JavaScript interface
5. **Session Management**: Persistent HTTP sessions for efficient web scraping

## Key Components

### 1. Main Application (`main.py`)
- **Purpose**: FastAPI application entry point and route definitions
- **Key Features**: 
  - REST API endpoint for insights extraction
  - Static file serving for frontend
  - Error handling with proper HTTP status codes
  - Logging configuration

### 2. Data Models (`models.py`)
- **Purpose**: Pydantic models defining the data structure
- **Key Models**:
  - `Product`: Individual product information
  - `BrandInsights`: Main response model containing all extracted data
  - `SocialHandles`: Social media presence
  - `ContactDetails`: Contact information
  - `ImportantLinks`: Key website navigation links

### 3. Scraping Services (`services/`)
- **`scraper.py`**: Main orchestrator service coordinating all scraping activities with AI validation
- **`product_scraper.py`**: Specialized service for extracting product catalogs from `/products.json` endpoint
- **`content_scraper.py`**: Service for extracting brand context, policies, and textual content
- **`social_scraper.py`**: Service for identifying and extracting social media handles
- **`ai_validator.py`**: AI-powered validation service using Gemini for content verification and improvement

### 4. Frontend Interface (`static/`)
- **`index.html`**: Bootstrap-based responsive web interface
- **`script.js`**: JavaScript for API communication and UI interactions
- **`style.css`**: Custom styling for enhanced user experience

### 5. Utilities (`utils/helpers.py`)
- **Purpose**: Common utility functions for URL validation and normalization
- **Features**: URL parsing, domain extraction, and input sanitization

## Data Flow

1. **User Input**: User submits Shopify store URL through web interface or API
2. **URL Validation**: System validates and normalizes the provided URL
3. **HTML Content Capture**: Initial page request captures HTML content for AI analysis
4. **Parallel Scraping**: Multiple specialized scrapers work concurrently:
   - Product scraper fetches from `/products.json` endpoints
   - Content scraper extracts homepage and policy pages
   - Social scraper identifies social media presence
5. **AI-Powered Validation**: Gemini AI validates each section:
   - Analyzes extracted content quality and completeness
   - Re-extracts data from HTML structure if validation fails
   - Provides intelligent content improvements
6. **Comprehensive Quality Assessment**: AI performs overall data quality analysis
7. **Data Aggregation**: Main scraper service combines validated results
8. **Response Formation**: Structured `BrandInsights` object with AI validation metadata returned as JSON
9. **Frontend Display**: Web interface presents data with quality scores and AI insights

## External Dependencies

### Core Libraries:
- **FastAPI**: Web framework for API development
- **Pydantic**: Data validation and settings management
- **Requests**: HTTP client for web scraping
- **BeautifulSoup4**: HTML parsing and extraction
- **Trafilatura**: Text extraction from web pages

### Frontend Dependencies:
- **Bootstrap 5.1.3**: CSS framework for responsive design
- **Font Awesome 6.0.0**: Icon library for enhanced UI

### Development Tools:
- **Logging**: Built-in Python logging for debugging and monitoring
- **Asyncio**: Asynchronous programming for improved performance

## Deployment Strategy

### Current Setup:
- **Static File Serving**: FastAPI serves static files directly
- **Single Process Architecture**: Synchronous scraping with session pooling
- **Error Handling**: Comprehensive exception handling with appropriate HTTP status codes

### Scalability Considerations:
- **Session Management**: Reusable HTTP sessions for efficiency
- **Modular Services**: Easy to extend with additional scraping capabilities
- **Async Ready**: Architecture supports future async/await implementation
- **Database Ready**: Models structured for potential database persistence

### Monitoring and Logging:
- **Structured Logging**: Comprehensive logging throughout the application
- **Error Tracking**: Detailed error messages and stack traces
- **Performance Monitoring**: Request/response timing capabilities

## Key Architectural Decisions

### 1. Service-Oriented Design
- **Problem**: Need to scrape diverse data types from different sources
- **Solution**: Separate specialized services for each data type
- **Benefits**: Maintainable, testable, and easily extensible

### 2. Pydantic Data Models
- **Problem**: Ensure data consistency and type safety
- **Solution**: Comprehensive Pydantic models with validation
- **Benefits**: Automatic data validation, clear API contracts, easy serialization

### 3. FastAPI Framework Choice
- **Problem**: Need high-performance API with automatic documentation
- **Solution**: FastAPI for modern Python web development
- **Benefits**: Automatic OpenAPI docs, type hints support, high performance

### 4. Scraping Without Official API
- **Problem**: Extract data without API access
- **Solution**: Public endpoint scraping (`/products.json`) combined with HTML parsing
- **Benefits**: No API keys required, works with any Shopify store

### 5. Frontend Integration
- **Problem**: Need user-friendly interface for testing
- **Solution**: Integrated static file serving with interactive web interface
- **Benefits**: Complete solution in one application, easy demonstration