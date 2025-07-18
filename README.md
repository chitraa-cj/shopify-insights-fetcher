# Shopify Store Insights Fetcher

A comprehensive Python-based web application that extracts brand insights from Shopify stores using advanced web scraping, AI validation with Gemini, and competitor analysis.

## Features

- **Complete Product Catalog Extraction**: Extracts all products from Shopify stores via `/products.json`
- **Hero Products Detection**: Identifies featured products displayed on the homepage
- **Policy Content Extraction**: Retrieves privacy policy, return policy, and terms of service with full content
- **Smart FAQ Extraction**: AI-powered FAQ extraction that filters out navigation menus
- **Social Media Detection**: Identifies Instagram, Facebook, TikTok, and other social handles
- **Contact Information**: Extracts emails, phone numbers, and addresses
- **Brand Context Analysis**: Gathers about us content and brand story
- **Currency Detection & Conversion**: Automatically detects store currency and converts to USD
- **Competitor Analysis**: Finds and analyzes similar Shopify stores
- **AI Content Validation**: Uses Gemini AI to validate and improve extracted content
- **PostgreSQL Persistence**: Stores all extracted data with full relationships

## Prerequisites

- Python 3.11+
- PostgreSQL database
- Gemini API key from Google AI Studio

## Installation & Setup

### 1. Environment Setup

```bash
# Clone the repository
git clone <repository-url>
cd shopify-insights-fetcher

# Install dependencies (using uv package manager)
uv sync
```

### 2. Environment Variables

Create a `.env` file or set environment variables:

```bash
# Required
GEMINI_API_KEY=your_gemini_api_key_here
DATABASE_URL=postgresql://username:password@localhost:5432/database_name

# PostgreSQL specific (if not using DATABASE_URL)
PGHOST=localhost
PGPORT=5432
PGUSER=your_username
PGPASSWORD=your_password
PGDATABASE=your_database_name
```

### 3. Database Setup

The application automatically creates all required tables on first run:

- `brand_insights`: Main brand information
- `products`: Product catalog with currency data
- `faqs`: Frequently asked questions
- `competitors`: Competitor analysis results

### 4. Running the Application

```bash
# Start the FastAPI server
uv run python main.py

# Server will start on http://0.0.0.0:5000
```

## API Endpoints

### 1. Extract Brand Insights

**Endpoint**: `POST /extract-insights`

**Description**: Main endpoint that extracts comprehensive brand insights from a Shopify store.

**Request Body**:
```json
{
  "website_url": "https://store.myshopify.com"
}
```

**Response**: Complete `BrandInsights` object with all extracted data

**Status Codes**:
- `200`: Success
- `401`: Website not found or not accessible
- `500`: Internal server error

**Postman Test**:
```bash
POST http://localhost:5000/extract-insights
Content-Type: application/json

{
  "website_url": "https://memy.co.in"
}
```

### 2. Get All Brands

**Endpoint**: `GET /database/brands`

**Description**: Retrieves summary of all brands stored in the database.

**Response**:
```json
{
  "brands": [
    {
      "store_url": "https://example.com",
      "brand_name": "Example Brand",
      "total_products": 150,
      "extraction_date": "2025-07-18T10:30:00"
    }
  ]
}
```

**Postman Test**:
```bash
GET http://localhost:5000/database/brands
```

### 3. Get Brand Details

**Endpoint**: `GET /database/brand/{store_url}`

**Description**: Retrieves detailed information for a specific brand from the database.

**Parameters**:
- `store_url`: URL-encoded store URL

**Response**: Complete brand data including products, FAQs, and competitors

**Postman Test**:
```bash
GET http://localhost:5000/database/brand/https%3A//memy.co.in
```

### 4. Web Interface

**Endpoint**: `GET /`

**Description**: Serves the web interface for testing the application.

**Postman Test**:
```bash
GET http://localhost:5000/
```

## Data Models

### BrandInsights (Main Response Model)

```json
{
  "website_url": "string",
  "brand_context": {
    "brand_name": "string",
    "brand_description": "string",
    "about_us_content": "string",
    "mission_statement": "string",
    "brand_story": "string"
  },
  "product_catalog": [
    {
      "id": "string",
      "title": "string",
      "price": "string",
      "price_usd": 29.99,
      "original_price": 25.99,
      "formatted_price": "₹2,099",
      "formatted_price_usd": "$29.99",
      "currency": "INR",
      "currency_symbol": "₹",
      "description": "string",
      "images": ["url1", "url2"],
      "tags": ["tag1", "tag2"],
      "vendor": "string",
      "product_type": "string",
      "available": true
    }
  ],
  "hero_products": [],
  "policies": {
    "privacy_policy_url": "string",
    "privacy_policy_content": "string",
    "return_policy_url": "string", 
    "return_policy_content": "string",
    "terms_of_service_url": "string",
    "terms_of_service_content": "string"
  },
  "faqs": [
    {
      "question": "Do you have COD as a payment option?",
      "answer": "Yes, we do have cash on delivery available."
    }
  ],
  "social_handles": {
    "instagram": "@brand_handle",
    "facebook": "@brand_page",
    "tiktok": "@brand_tiktok",
    "twitter": "@brand_twitter",
    "youtube": "channel_url",
    "linkedin": "company_url",
    "pinterest": "profile_url"
  },
  "contact_details": {
    "emails": ["contact@brand.com"],
    "phone_numbers": ["+1-234-567-8900"],
    "address": "123 Main St, City, Country"
  },
  "important_links": {
    "order_tracking": "url",
    "contact_us": "url",
    "blogs": "url",
    "size_guide": "url",
    "shipping_info": "url",
    "about_us": "url",
    "careers": "url"
  },
  "competitor_analysis": {
    "competitors_found": 3,
    "competitor_insights": [
      {
        "store_url": "competitor-url",
        "brand_name": "Competitor Name",
        "product_count": 100,
        "price_range": "$10-$100",
        "social_presence_score": 85,
        "key_features": ["feature1", "feature2"],
        "strengths": ["strength1"],
        "weaknesses": ["weakness1"]
      }
    ],
    "competitive_analysis": "AI-generated analysis",
    "market_positioning": "Position description"
  },
  "ai_validation": {
    "validated": true,
    "confidence_score": 0.85,
    "validation_notes": ["note1", "note2"]
  },
  "detected_currency": "INR",
  "currency_symbol": "₹",
  "total_products_found": 222,
  "extraction_timestamp": "2025-07-18T10:30:00.000Z",
  "extraction_success": true,
  "errors": []
}
```

## Postman Collection Setup

### 1. Create New Collection
- Name: "Shopify Insights Fetcher"
- Base URL: `http://localhost:5000`

### 2. Environment Variables
Create environment with:
- `base_url`: `http://localhost:5000`
- `test_store`: `https://memy.co.in`

### 3. Test Requests

#### Extract Insights (Main Test)
```
POST {{base_url}}/extract-insights
Body (JSON):
{
  "website_url": "{{test_store}}"
}
```

#### Get All Brands
```
GET {{base_url}}/database/brands
```

#### Get Specific Brand
```
GET {{base_url}}/database/brand/{{test_store}}
```

#### Health Check
```
GET {{base_url}}/
```

## Testing Instructions

### 1. Basic Functionality Test

```bash
# Test main extraction endpoint
curl -X POST "http://localhost:5000/extract-insights" \
  -H "Content-Type: application/json" \
  -d '{"website_url": "https://memy.co.in"}'
```

### 2. Error Handling Test

```bash
# Test invalid URL (should return 401)
curl -X POST "http://localhost:5000/extract-insights" \
  -H "Content-Type: application/json" \
  -d '{"website_url": "https://invalid-store.com"}'
```

### 3. Database Endpoints Test

```bash
# Get all brands
curl -X GET "http://localhost:5000/database/brands"

# Get specific brand
curl -X GET "http://localhost:5000/database/brand/https%3A//memy.co.in"
```

## Database Schema

### brand_insights
- `id`: Primary key
- `store_url`: Unique store URL
- `brand_name`: Extracted brand name
- `brand_description`: Brand description
- `total_products_found`: Product count
- `ai_confidence_score`: AI validation score
- `social_handles`: JSON of social media handles
- `contact_details`: JSON of contact information
- `policies`: JSON of policy information
- `important_links`: JSON of important links
- `extraction_timestamp`: When data was extracted

### products
- `id`: Primary key
- `brand_insights_id`: Foreign key to brand_insights
- `product_id`: Shopify product ID
- `product_name`: Product title
- `price`: Product price (converted to USD)
- `currency`: Original currency
- `description`: Product description
- `image_url`: Primary product image
- `tags`: JSON array of tags
- `is_hero_product`: Boolean flag

### faqs
- `id`: Primary key
- `brand_insights_id`: Foreign key to brand_insights
- `question`: FAQ question
- `answer`: FAQ answer

### competitors
- `id`: Primary key
- `brand_insights_id`: Foreign key to brand_insights
- `competitor_url`: Competitor store URL
- `competitor_name`: Competitor brand name
- `product_count`: Number of products
- `price_range`: Price range description
- `social_presence_score`: Social media presence score
- `key_features`: JSON array of features
- `strengths`: JSON array of strengths
- `weaknesses`: JSON array of weaknesses

## Key Features Verification

### ✅ Working Features
1. **Product Catalog**: Extracts complete product list from `/products.json`
2. **Hero Products**: Identifies homepage featured products
3. **Currency Detection**: Automatically detects and converts currencies
4. **Policy Extraction**: Retrieves actual policy content, not just URLs
5. **FAQ Extraction**: AI-filtered FAQs that avoid navigation menus
6. **Social Handles**: Detects Instagram, Facebook, TikTok, etc.
7. **Contact Details**: Extracts emails, phones, addresses
8. **Brand Context**: About us and brand story extraction
9. **AI Validation**: Gemini AI validates and improves content
10. **Competitor Analysis**: Finds and analyzes similar stores
11. **Database Persistence**: Stores all data in PostgreSQL
12. **Error Handling**: Proper HTTP status codes (401, 500)

### 🔧 Technical Details
- **Processing Time**: 30-60 seconds per store (due to AI validation)
- **Concurrent Processing**: Multiple extraction tasks run in parallel
- **AI Calls**: ~10-15 Gemini API calls per extraction
- **Database**: Auto-creates tables and relationships
- **Currency Support**: Detects 50+ currencies, converts to USD
- **Error Recovery**: AI re-analyzes HTML when initial extraction fails

## Troubleshooting

### Common Issues

1. **Database Connection Error**
   - Verify PostgreSQL is running
   - Check DATABASE_URL format
   - Ensure database exists

2. **Gemini API Error**
   - Verify GEMINI_API_KEY is set
   - Check API quota limits
   - Ensure key has proper permissions

3. **Slow Response Times**
   - Normal for AI validation (30-60s)
   - Consider reducing AI validation calls for faster testing

4. **Product/FAQ Not Saving**
   - Check database logs
   - Verify table schema matches models
   - Check for data type mismatches

### Log Monitoring

```bash
# Monitor application logs
tail -f application.log

# Check database connectivity
python -c "import asyncpg; print('Database module available')"
```

## Performance Notes

- **Average Extraction Time**: 45-60 seconds
- **Products Processed**: Up to 1000 products per store
- **AI Validation**: 10-15 API calls per extraction
- **Database Operations**: Atomic transactions with rollback support
- **Memory Usage**: ~50MB per extraction process

## API Rate Limits

- **Gemini API**: Standard quotas apply
- **Target Websites**: Respectful scraping with delays
- **Database**: No artificial limits

## Support

For issues, check:
1. Application logs for detailed error messages
2. Database connection status
3. Gemini API key validity
4. Network connectivity to target websites

## License

[Your License Here]