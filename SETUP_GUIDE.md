# Shopify Store Insights Fetcher - Setup Guide

## Quick Start

1. **Basic Setup** (works immediately)
   ```bash
   # All core dependencies are already installed
   # Start the application
   python main.py
   ```

2. **Access the Application**
   - Web Interface: http://localhost:5000
   - API Documentation: http://localhost:5000/docs

## Environment Configuration

### Required (Already Set)
- `DATABASE_URL` - PostgreSQL connection (automatically configured)
- `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE` - Database credentials

### Optional (Enhances Features)
- `GEMINI_API_KEY` - Enables AI validation and content improvement

## Getting Gemini API Key (Optional)

### Why Add Gemini API Key?
Adding the Gemini API key enhances the application with:
- **Intelligent Content Validation** - AI verifies extracted content quality
- **Smart FAQ Filtering** - Better removal of navigation menus from FAQ sections
- **Enhanced Policy Analysis** - AI validation of policy completeness
- **Quality Scoring** - Overall assessment of extraction accuracy
- **Content Improvement** - AI-powered enhancement of extracted data

### How to Get Your API Key
1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the generated key
5. Add it to your environment variables

### Adding the API Key
1. In Replit, go to "Secrets" (lock icon in sidebar)
2. Add a new secret:
   - Key: `GEMINI_API_KEY`
   - Value: Your API key from Google AI Studio
3. Restart the application

## Application Features

### ✅ Always Available (No API Key Required)
- **Product Extraction** - Complete product catalogs and hero products
- **Currency Detection** - Automatic price conversion between currencies
- **FAQ Scraping** - Basic FAQ extraction from HTML structure
- **Policy Extraction** - Policy links and content retrieval
- **Social Media Detection** - Social platform handle extraction
- **Contact Information** - Email, phone, and address extraction
- **Competitor Analysis** - Discovery of similar Shopify stores
- **Database Storage** - All data persisted in PostgreSQL
- **Web Interface** - Full frontend functionality with currency switching

### 🤖 AI-Enhanced (Requires GEMINI_API_KEY)
- **Content Quality Assessment** - AI rates extraction accuracy
- **Smart Content Filtering** - Better removal of navigation elements
- **Intelligent Validation** - AI verifies and improves extracted content
- **Comprehensive Analysis** - Overall quality scoring and recommendations

## Testing the Application

### Without API Key
```bash
# The application will show this warning on startup:
# ⚠️  GEMINI_API_KEY not found - AI validation features will be disabled
# ✅ All core features work normally
```

### With API Key
```bash
# The application will show:
# ✅ Gemini AI validation enabled
# ✅ All features available including AI enhancements
```

## API Usage Examples

### Extract Store Insights
```bash
curl -X POST "http://localhost:5000/extract-insights" \
  -H "Content-Type: application/json" \
  -d '{"website_url": "https://memy.co.in"}'
```

### View Database Content
```bash
# List all stored brands
curl "http://localhost:5000/database/brands"

# Get specific brand data
curl "http://localhost:5000/database/brand/https://memy.co.in"
```

## Troubleshooting

### Common Issues
1. **"Website not found or unreachable"** - Check if the URL is accessible
2. **Empty results** - Some stores may have restricted access to product data
3. **AI features not working** - Verify GEMINI_API_KEY is correctly set

### Getting Help
- Check the application logs for detailed error messages
- Review TESTING_GUIDE.md for comprehensive test scenarios
- Use the Postman collection for API testing

## Performance Notes
- First-time extraction takes 30-60 seconds for comprehensive analysis
- Subsequent requests are faster due to caching
- AI validation adds ~10-15 seconds but significantly improves data quality