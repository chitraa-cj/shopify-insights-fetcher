from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, HttpUrl
import logging
import traceback
from services.scraper import ShopifyScraperService
from models import BrandInsights

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Shopify Store Insights Fetcher",
    description="Extract comprehensive brand insights from Shopify stores",
    version="1.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

class WebsiteRequest(BaseModel):
    website_url: HttpUrl

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main HTML page"""
    with open("static/index.html", "r") as f:
        return HTMLResponse(content=f.read())

@app.post("/extract-insights", response_model=BrandInsights)
async def extract_brand_insights(request: WebsiteRequest):
    """
    Extract comprehensive brand insights from a Shopify store
    
    Args:
        request: WebsiteRequest containing the Shopify store URL
        
    Returns:
        BrandInsights: Structured brand information
        
    Raises:
        HTTPException: 401 if website not found, 500 for internal errors
    """
    try:
        url = str(request.website_url)
        logger.info(f"Starting extraction for URL: {url}")
        
        # Initialize scraper service
        scraper_service = ShopifyScraperService()
        
        # Extract insights
        insights = await scraper_service.extract_all_insights(url)
        
        logger.info(f"Successfully extracted insights for {url}")
        return insights
        
    except ValueError as e:
        logger.error(f"Invalid website URL: {e}")
        raise HTTPException(status_code=401, detail=f"Website not found or invalid: {str(e)}")
    
    except ConnectionError as e:
        logger.error(f"Connection error for {url}: {e}")
        raise HTTPException(status_code=401, detail="Website not found or unreachable")
    
    except Exception as e:
        logger.error(f"Internal error while processing {url}: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Shopify Insights Fetcher"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
