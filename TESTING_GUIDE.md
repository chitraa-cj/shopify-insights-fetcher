# Shopify Insights Fetcher - Testing Guide

## Quick Start Testing

### 1. Server Health Check
```bash
curl -X GET "http://localhost:5000/"
# Expected: HTML response with web interface
```

### 2. Basic Functionality Test
```bash
curl -X POST "http://localhost:5000/extract-insights" \
  -H "Content-Type: application/json" \
  -d '{"website_url": "https://memy.co.in"}' \
  -w "\nStatus Code: %{http_code}\n"
# Expected: 200 status with full BrandInsights JSON
```

### 3. Error Handling Test
```bash
curl -X POST "http://localhost:5000/extract-insights" \
  -H "Content-Type: application/json" \
  -d '{"website_url": "https://invalid-store.com"}' \
  -w "\nStatus Code: %{http_code}\n"
# Expected: 401 status with error message
```

### 4. Database Verification
```bash
curl -X GET "http://localhost:5000/database/brands"
# Expected: List of extracted brands with metadata
```

## Postman Collection Import

1. Import `Shopify_Insights_Fetcher.postman_collection.json`
2. Set environment variables:
   - `base_url`: `http://localhost:5000`
   - `test_store`: `https://memy.co.in`
3. Run the collection to test all endpoints

## Comprehensive Test Scenarios

### Test Case 1: Full Extraction Workflow
**Objective**: Verify complete brand insights extraction

**Steps**:
1. POST to `/extract-insights` with valid Shopify store
2. Wait for completion (30-60 seconds)
3. Verify response contains all required fields
4. Check database storage with `/database/brands`

**Expected Results**:
- Status: 200
- Response includes: products, FAQs, policies, social handles, contact details
- Currency detection and conversion working
- Database entry created

### Test Case 2: Currency Detection
**Objective**: Test automatic currency detection and conversion

**Test Stores**:
- Indian store (INR): `https://memy.co.in`
- US store (USD): `https://allbirds.com`
- European store (EUR): `https://www.weekday.com`

**Verification**:
- Check `detected_currency` field
- Verify `price_usd` conversion
- Confirm `formatted_price` with original currency

### Test Case 3: Error Handling
**Objective**: Verify proper error responses

**Test Cases**:
```bash
# Invalid domain
{"website_url": "https://nonexistent-store.xyz"}
# Expected: 401

# Non-Shopify site  
{"website_url": "https://google.com"}
# Expected: 200 with limited data (graceful handling)

# Malformed URL
{"website_url": "not-a-url"}
# Expected: 401
```

### Test Case 4: Database Operations
**Objective**: Test data persistence and retrieval

**Steps**:
1. Extract insights for multiple stores
2. List all brands: `GET /database/brands`
3. Get specific brand: `GET /database/brand/{url}`
4. Verify data consistency

### Test Case 5: Content Quality Verification
**Objective**: Verify AI validation is working

**Check Points**:
- FAQs are actual questions, not navigation menus
- Policies contain full content, not just URLs
- Social handles are properly formatted
- Contact details are real emails/phones

## Performance Testing

### Load Testing
```bash
# Test concurrent requests (use carefully)
for i in {1..3}; do
  curl -X POST "http://localhost:5000/extract-insights" \
    -H "Content-Type: application/json" \
    -d '{"website_url": "https://different-store-'$i'.myshopify.com"}' &
done
```

### Response Time Monitoring
```bash
curl -X POST "http://localhost:5000/extract-insights" \
  -H "Content-Type: application/json" \
  -d '{"website_url": "https://memy.co.in"}' \
  -w "Total time: %{time_total}s\n"
# Expected: 30-90 seconds depending on store complexity
```

## Data Validation Checklist

### ✅ Product Catalog
- [ ] Products extracted from `/products.json`
- [ ] Currency detected and converted
- [ ] Images, prices, descriptions populated
- [ ] Hero products identified separately

### ✅ Policies 
- [ ] Privacy policy URL and content
- [ ] Return policy URL and content  
- [ ] Terms of service URL and content
- [ ] Content is substantial (not just navigation)

### ✅ FAQs
- [ ] Questions end with "?"
- [ ] Answers are informative
- [ ] No navigation menu items
- [ ] Customer service related content

### ✅ Social Media
- [ ] Instagram handle extracted
- [ ] Facebook page found
- [ ] TikTok (for non-India brands)
- [ ] Twitter/LinkedIn if available

### ✅ Contact Details
- [ ] Email addresses found
- [ ] Phone numbers with country codes
- [ ] Physical address if available

### ✅ Technical Features
- [ ] AI validation confidence > 0.5
- [ ] Competitor analysis completed
- [ ] Database storage successful
- [ ] Error handling working

## Troubleshooting Tests

### Database Connection Test
```bash
# Check if database is accessible
python3 -c "
import asyncio
import asyncpg
import os

async def test_db():
    try:
        conn = await asyncpg.connect(os.environ['DATABASE_URL'])
        result = await conn.fetchval('SELECT 1')
        print(f'Database connection: OK (result: {result})')
        await conn.close()
    except Exception as e:
        print(f'Database error: {e}')

asyncio.run(test_db())
"
```

### Gemini API Test
```bash
# Test API key validity
python3 -c "
import os
from google import genai

try:
    client = genai.Client(api_key=os.environ.get('GEMINI_API_KEY'))
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents='Hello, test message'
    )
    print('Gemini API: OK')
except Exception as e:
    print(f'Gemini API error: {e}')
"
```

## Performance Benchmarks

### Expected Metrics
- **Small Store** (< 50 products): 20-30 seconds
- **Medium Store** (50-200 products): 30-45 seconds  
- **Large Store** (200+ products): 45-90 seconds

### Memory Usage
- Base application: ~30MB
- During extraction: ~50-80MB
- Database connections: ~10MB

### AI API Calls
- Brand context: 2-3 calls
- Policy extraction: 2-4 calls
- FAQ validation: 1-2 calls
- Social handles: 1-2 calls
- Contact details: 1-2 calls
- Competitor analysis: 3-5 calls
- **Total per extraction**: 10-18 calls

## Common Issues & Solutions

### Issue: Slow Response Times
**Cause**: Multiple AI validation calls
**Solution**: Normal behavior, wait for completion

### Issue: Products Not Saved
**Cause**: Database schema mismatch
**Solution**: Check logs, verify table structure

### Issue: Empty FAQs
**Cause**: Store doesn't have dedicated FAQ section
**Solution**: Expected behavior, some stores lack FAQs

### Issue: Currency Not Detected
**Cause**: Store uses images for prices
**Solution**: Fallback to USD, manual verification needed

### Issue: Competitor Analysis Empty
**Cause**: No similar stores found
**Solution**: Expected for very niche products

## Test Data Examples

### Valid Shopify Stores for Testing
- **Fashion**: `https://memy.co.in` (India, INR)
- **Apparel**: `https://allbirds.com` (US, USD)
- **Beauty**: `https://glossier.com` (US, USD)
- **Electronics**: `https://www.tesla.com/shop` (Global, USD)

### Invalid URLs for Error Testing
- `https://invalid-domain.xyz`
- `https://google.com` (non-Shopify)
- `not-a-valid-url`
- `https://store-that-does-not-exist.myshopify.com`

## Automated Testing Script

```bash
#!/bin/bash
echo "Running Shopify Insights Fetcher Tests..."

# Test 1: Health check
echo "Test 1: Health Check"
curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/
echo ""

# Test 2: Valid extraction
echo "Test 2: Valid Store Extraction"
curl -s -X POST "http://localhost:5000/extract-insights" \
  -H "Content-Type: application/json" \
  -d '{"website_url": "https://memy.co.in"}' \
  -w "Status: %{http_code}, Time: %{time_total}s\n" \
  -o /dev/null

# Test 3: Invalid store
echo "Test 3: Invalid Store"
curl -s -X POST "http://localhost:5000/extract-insights" \
  -H "Content-Type: application/json" \
  -d '{"website_url": "https://invalid.com"}' \
  -w "Status: %{http_code}\n" \
  -o /dev/null

# Test 4: Database check
echo "Test 4: Database Access"
curl -s -w "Status: %{http_code}\n" \
  -o /dev/null \
  http://localhost:5000/database/brands

echo "Tests completed!"
```

Save this as `run_tests.sh` and execute with `bash run_tests.sh`