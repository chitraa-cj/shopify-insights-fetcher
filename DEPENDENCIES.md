# Project Dependencies Documentation

## Core Dependencies

### Web Framework
- **FastAPI**: Modern, fast (high-performance) web framework for building APIs with Python 3.6+
- **Uvicorn**: ASGI server for running FastAPI applications
- **Pydantic**: Data validation and settings management using Python type annotations

### Web Scraping & Content Extraction
- **Requests**: HTTP library for making web requests
- **BeautifulSoup4**: Library for parsing HTML and XML documents
- **Trafilatura**: Tool for extracting main text content from web pages
- **AIOHTTP**: Asynchronous HTTP client/server framework

### AI Integration
- **Google GenAI**: Official Google AI SDK for Gemini models
  - Used for intelligent content extraction and validation
  - Enables AI reasoning for complex site navigation
  - Supports JSON structured outputs for reliable data extraction

### Database
- **AsyncPG**: Fast PostgreSQL database interface library for Python
- **PostgreSQL**: Production-ready relational database for data persistence

### Development & Utilities
- **Logging**: Built-in Python logging for debugging and monitoring
- **Asyncio**: Asynchronous programming support
- **JSON**: Data serialization and API responses
- **urllib.parse**: URL parsing and manipulation
- **re**: Regular expressions for pattern matching

## AI-Powered Features

### Intelligent Content Extraction
The system leverages Gemini AI for:

1. **Policy Discovery**: AI analyzes website structure to find policy pages
2. **Content Enhancement**: Cleans and organizes extracted policy content
3. **FAQ Navigation**: Intelligently discovers expandable FAQ sections
4. **Link Analysis**: Uses context to determine relevant content links
5. **Content Validation**: Ensures extracted content quality and relevance

### Fallback Mechanisms
- Traditional regex-based extraction when AI is unavailable
- Multiple extraction strategies for robustness
- Graceful degradation without breaking core functionality

## Environment Variables

### Required
- `DATABASE_URL`: PostgreSQL connection string
- `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`: Database connection details

### Optional
- `GEMINI_API_KEY`: Enables AI-powered content extraction features
  - Without this key, system falls back to traditional extraction methods
  - Recommended for enhanced policy and FAQ extraction capabilities

## System Architecture Dependencies

### SOLID Design Principles
The project follows SOLID principles with these architectural dependencies:

1. **Interface-Based Design**: Clear contracts between components
2. **Dependency Injection**: Services are injected rather than created directly
3. **Factory Pattern**: Centralized service creation with proper dependencies
4. **Circuit Breakers**: Prevent cascading failures
5. **Health Monitoring**: Service status tracking and metrics

### Error Handling Dependencies
- **Retry Mechanisms**: Exponential backoff for transient failures
- **Rate Limiting**: Prevents service overload
- **Circuit Breakers**: Automatic failure detection and recovery
- **Comprehensive Logging**: Detailed error tracking and debugging

## Performance Optimizations

### Session Management
- **HTTP Session Pooling**: Reuses connections for efficiency
- **Connection Timeouts**: Prevents hanging requests
- **Request Retry Logic**: Handles temporary network issues

### Concurrent Processing
- **Parallel Extraction**: Multiple scrapers work simultaneously
- **Async/Await Support**: Non-blocking operations where possible
- **Resource Management**: Proper cleanup and resource disposal

## Development Workflow

### Testing Dependencies
- **Pytest**: Testing framework (development)
- **Mock**: Testing utilities for service mocking
- **Edge Case Testing**: Comprehensive error scenario coverage

### Code Quality
- **Type Hints**: Full type annotation support
- **Documentation**: Comprehensive inline and external documentation
- **Error Handling**: Graceful failure management

## Deployment Dependencies

### Production Requirements
- **PostgreSQL Server**: Database hosting
- **Python 3.8+**: Runtime environment
- **Process Manager**: For production deployment (e.g., Gunicorn, systemd)
- **Reverse Proxy**: Nginx or similar for production traffic handling

### Monitoring
- **Health Checks**: Built-in service monitoring
- **Metrics Collection**: Performance and error tracking
- **Log Aggregation**: Centralized logging for debugging

## Future Extension Points

### Planned Dependencies
- **Redis**: Caching layer for improved performance
- **Celery**: Background task processing for long-running extractions
- **Prometheus**: Advanced metrics collection
- **Elasticsearch**: Enhanced search and analytics capabilities

### AI Enhancement Opportunities
- **Multiple AI Providers**: Support for OpenAI, Anthropic, etc.
- **Specialized Models**: Industry-specific content extraction models
- **Machine Learning**: Custom models for brand recognition and categorization

This dependency structure ensures scalability, maintainability, and extensibility while providing robust error handling and performance optimization.