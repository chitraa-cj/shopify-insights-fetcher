# Shopify Store Insights Fetcher - Functionality Verification

## Required Functionalities:

1. ✓ **Product Catalog** - Full list of products from /products.json
2. ✓ **Hero Products** - Products displayed on homepage
3. ✓ **Privacy Policy** - URL and content extraction
4. ✓ **Return/Refund Policies** - URL and content extraction  
5. ✓ **Brand FAQs** - Customer service Q&A pairs
6. ✓ **Social Handles** - Instagram, Facebook, TikTok, etc.
7. ✓ **Contact Details** - Email, phone, address
8. ✓ **Brand Context** - About us content
9. ✓ **Important Links** - Order tracking, contact, blogs
10. ✓ **Currency Detection** - Automatic currency conversion
11. ✓ **Database Persistence** - Save all data to PostgreSQL
12. ✓ **Competitor Analysis** - Automatic competitor finding

## API Requirements:
- POST /extract-insights with website_url
- JSON response with Brand Context object
- Error handling: 401 for not found, 500 for internal errors
- LLM double-checking for content validation

## Database Verification:
- Products saved with currency information
- FAQs extracted and stored
- Policies with actual content
- Social handles detected
- Contact details extracted
