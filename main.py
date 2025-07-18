from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, HttpUrl
import logging
import traceback
import requests
import os
from services.scraper import ShopifyScraperService
from services.database_service import DatabaseService
from models import BrandInsights

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check for Gemini API key and warn if missing
if not os.environ.get("GEMINI_API_KEY"):
    logger.warning("⚠️  GEMINI_API_KEY not found - AI validation features will be disabled")
    logger.warning("   To enable AI features, provide your Gemini API key in the environment variables")
else:
    logger.info("✅ Gemini AI validation enabled")

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
    
    except (ConnectionError, requests.exceptions.ConnectionError) as e:
        logger.error(f"Connection error for {url}: {e}")
        raise HTTPException(status_code=401, detail="Website not found or unreachable")
    
    except Exception as e:
        logger.error(f"Internal error while processing {url}: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/database/brands")
async def get_all_brands():
    """Get summary of all brands stored in database"""
    try:
        db_service = DatabaseService()
        await db_service.initialize()
        brands = await db_service.get_all_brands()
        await db_service.close()
        return {"brands": brands}
    except Exception as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/database/brand/{store_url:path}")
async def get_brand_details(store_url: str):
    """Get detailed brand information from database"""
    try:
        db_service = DatabaseService()
        await db_service.initialize()
        brand_data = await db_service.get_brand_insights(store_url)
        await db_service.close()
        
        if not brand_data:
            raise HTTPException(status_code=404, detail="Brand not found in database")
        
        return brand_data
    except Exception as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {"status": "healthy", "service": "Shopify Insights Fetcher"}

@app.get("/health/comprehensive")
async def comprehensive_health_check():
    """Comprehensive health check with all dependencies"""
    try:
        from services.health_checker import SystemHealthChecker
        
        health_checker = SystemHealthChecker()
        await health_checker.initialize()
        
        result = await health_checker.check_health()
        await health_checker.cleanup()
        
        if result.is_success:
            return result.data
        else:
            raise HTTPException(status_code=500, detail=f"Health check failed: {result.error_message}")
    
    except Exception as e:
        logger.error(f"Comprehensive health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check error: {str(e)}")

@app.get("/metrics")
async def get_system_metrics():
    """Get system performance metrics"""
    try:
        from services.health_checker import SystemHealthChecker
        
        health_checker = SystemHealthChecker()
        summary = health_checker.get_health_summary()
        
        return {
            "metrics": summary,
            "timestamp": time.time(),
            "uptime": "Not implemented yet"  # Could add process start time tracking
        }
    
    except Exception as e:
        logger.error(f"Metrics endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=f"Metrics error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
