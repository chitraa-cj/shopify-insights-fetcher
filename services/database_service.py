import logging
import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
import asyncpg
from pydantic import BaseModel

from models import BrandInsights, Product, FAQ, CompetitorInfo

logger = logging.getLogger(__name__)

class DatabaseService:
    """Service for persisting brand insights and competitor data to PostgreSQL"""
    
    def __init__(self):
        self.database_url = os.environ.get('DATABASE_URL')
        self.pool = None
    
    async def initialize(self):
        """Initialize database connection and create tables"""
        try:
            self.pool = await asyncpg.create_pool(self.database_url, min_size=1, max_size=5)
            await self._create_tables()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def _create_tables(self):
        """Create database tables if they don't exist"""
        async with self.pool.acquire() as conn:
            # Brand insights table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS brand_insights (
                    id SERIAL PRIMARY KEY,
                    store_url VARCHAR(500) UNIQUE NOT NULL,
                    brand_name VARCHAR(200),
                    brand_description TEXT,
                    about_us_content TEXT,
                    brand_story TEXT,
                    total_products_found INTEGER DEFAULT 0,
                    extraction_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ai_confidence_score FLOAT DEFAULT 0.0,
                    market_positioning VARCHAR(200),
                    competitive_analysis TEXT,
                    social_handles JSONB,
                    contact_details JSONB,
                    policies JSONB,
                    important_links JSONB,
                    errors JSONB,
                    raw_data JSONB
                )
            ''')
            
            # Products table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    brand_insights_id INTEGER REFERENCES brand_insights(id) ON DELETE CASCADE,
                    product_id VARCHAR(100),
                    product_name VARCHAR(500),
                    product_type VARCHAR(200),
                    price DECIMAL(10,2),
                    currency VARCHAR(10),
                    description TEXT,
                    image_url VARCHAR(1000),
                    tags JSONB,
                    is_hero_product BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # FAQs table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS faqs (
                    id SERIAL PRIMARY KEY,
                    brand_insights_id INTEGER REFERENCES brand_insights(id) ON DELETE CASCADE,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Competitors table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS competitors (
                    id SERIAL PRIMARY KEY,
                    brand_insights_id INTEGER REFERENCES brand_insights(id) ON DELETE CASCADE,
                    competitor_url VARCHAR(500) NOT NULL,
                    competitor_name VARCHAR(200),
                    product_count INTEGER DEFAULT 0,
                    price_range VARCHAR(100),
                    social_presence_score INTEGER DEFAULT 0,
                    key_features JSONB,
                    strengths JSONB,
                    weaknesses JSONB,
                    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for better performance
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_brand_insights_url ON brand_insights(store_url)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_products_brand_id ON products(brand_insights_id)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_competitors_brand_id ON competitors(brand_insights_id)')
    
    async def save_brand_insights(self, insights: BrandInsights) -> Optional[int]:
        """Save brand insights to database and return the record ID"""
        try:
            async with self.pool.acquire() as conn:
                # Insert or update brand insights
                brand_id = await conn.fetchval('''
                    INSERT INTO brand_insights (
                        store_url, brand_name, brand_description, about_us_content, 
                        brand_story, total_products_found, ai_confidence_score,
                        market_positioning, competitive_analysis, social_handles,
                        contact_details, policies, important_links, errors, raw_data
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                    ON CONFLICT (store_url) DO UPDATE SET
                        brand_name = EXCLUDED.brand_name,
                        brand_description = EXCLUDED.brand_description,
                        about_us_content = EXCLUDED.about_us_content,
                        brand_story = EXCLUDED.brand_story,
                        total_products_found = EXCLUDED.total_products_found,
                        ai_confidence_score = EXCLUDED.ai_confidence_score,
                        market_positioning = EXCLUDED.market_positioning,
                        competitive_analysis = EXCLUDED.competitive_analysis,
                        social_handles = EXCLUDED.social_handles,
                        contact_details = EXCLUDED.contact_details,
                        policies = EXCLUDED.policies,
                        important_links = EXCLUDED.important_links,
                        errors = EXCLUDED.errors,
                        raw_data = EXCLUDED.raw_data,
                        extraction_timestamp = CURRENT_TIMESTAMP
                    RETURNING id
                ''', 
                    insights.website_url,
                    insights.brand_context.brand_name if insights.brand_context else None,
                    insights.brand_context.brand_description if insights.brand_context else None,
                    insights.brand_context.about_us_content if insights.brand_context else None,
                    insights.brand_context.brand_story if insights.brand_context else None,
                    insights.total_products_found,
                    insights.ai_validation.confidence_score if insights.ai_validation else 0.0,
                    insights.competitor_analysis.market_positioning if insights.competitor_analysis else None,
                    insights.competitor_analysis.competitive_analysis if insights.competitor_analysis else None,
                    json.dumps(insights.social_handles.dict()) if insights.social_handles else None,
                    json.dumps(insights.contact_details.dict()) if insights.contact_details else None,
                    json.dumps(insights.policies.dict()) if insights.policies else None,
                    json.dumps(insights.important_links.dict()) if insights.important_links else None,
                    json.dumps(insights.errors),
                    json.dumps(insights.dict(), default=str)
                )
                
                if brand_id:
                    # Clear existing related data
                    await conn.execute('DELETE FROM products WHERE brand_insights_id = $1', brand_id)
                    await conn.execute('DELETE FROM faqs WHERE brand_insights_id = $1', brand_id)
                    await conn.execute('DELETE FROM competitors WHERE brand_insights_id = $1', brand_id)
                    
                    # Save products
                    await self._save_products(conn, brand_id, insights.product_catalog, insights.hero_products)
                    
                    # Save FAQs
                    await self._save_faqs(conn, brand_id, insights.faqs)
                    
                    # Save competitors
                    if insights.competitor_analysis and insights.competitor_analysis.competitor_insights:
                        await self._save_competitors(conn, brand_id, insights.competitor_analysis.competitor_insights)
                    
                    logger.info(f"Successfully saved insights for {insights.website_url} with ID {brand_id}")
                    return brand_id
                
        except Exception as e:
            logger.error(f"Error saving brand insights: {e}")
            return None
    
    async def _save_products(self, conn, brand_id: int, products: List[Product], hero_products: List[Product]):
        """Save products to database"""
        hero_product_ids = {p.product_id for p in hero_products} if hero_products else set()
        
        for product in products:
            await conn.execute('''
                INSERT INTO products (
                    brand_insights_id, product_id, product_name, product_type,
                    price, currency, description, image_url, tags, is_hero_product
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ''',
                brand_id,
                product.product_id,
                product.title,
                product.product_type,
                float(product.price) if product.price and str(product.price).replace('.', '').isdigit() else None,
                'USD',  # Default currency
                product.description,
                product.image_url,
                json.dumps(product.tags) if product.tags else None,
                product.product_id in hero_product_ids
            )
    
    async def _save_faqs(self, conn, brand_id: int, faqs: List[FAQ]):
        """Save FAQs to database"""
        for faq in faqs:
            await conn.execute('''
                INSERT INTO faqs (brand_insights_id, question, answer)
                VALUES ($1, $2, $3)
            ''', brand_id, faq.question, faq.answer)
    
    async def _save_competitors(self, conn, brand_id: int, competitors: List[CompetitorInfo]):
        """Save competitors to database"""
        for competitor in competitors:
            await conn.execute('''
                INSERT INTO competitors (
                    brand_insights_id, competitor_url, competitor_name,
                    product_count, price_range, social_presence_score,
                    key_features, strengths, weaknesses
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ''',
                brand_id,
                competitor.store_url,
                competitor.brand_name,
                competitor.product_count,
                competitor.price_range,
                competitor.social_presence_score,
                json.dumps(competitor.key_features),
                json.dumps(competitor.strengths),
                json.dumps(competitor.weaknesses)
            )
    
    async def get_brand_insights(self, store_url: str) -> Optional[Dict[str, Any]]:
        """Retrieve brand insights from database"""
        try:
            async with self.pool.acquire() as conn:
                # Get main brand data
                brand_data = await conn.fetchrow('''
                    SELECT * FROM brand_insights WHERE store_url = $1
                ''', store_url)
                
                if not brand_data:
                    return None
                
                brand_id = brand_data['id']
                
                # Get related data
                products = await conn.fetch('''
                    SELECT * FROM products WHERE brand_insights_id = $1
                ''', brand_id)
                
                faqs = await conn.fetch('''
                    SELECT * FROM faqs WHERE brand_insights_id = $1
                ''', brand_id)
                
                competitors = await conn.fetch('''
                    SELECT * FROM competitors WHERE brand_insights_id = $1
                ''', brand_id)
                
                # Compile results
                return {
                    'brand_data': dict(brand_data),
                    'products': [dict(p) for p in products],
                    'faqs': [dict(f) for f in faqs],
                    'competitors': [dict(c) for c in competitors]
                }
                
        except Exception as e:
            logger.error(f"Error retrieving brand insights: {e}")
            return None
    
    async def get_all_brands(self) -> List[Dict[str, Any]]:
        """Get summary of all brands in database"""
        try:
            async with self.pool.acquire() as conn:
                brands = await conn.fetch('''
                    SELECT 
                        store_url, brand_name, total_products_found,
                        ai_confidence_score, extraction_timestamp,
                        market_positioning
                    FROM brand_insights 
                    ORDER BY extraction_timestamp DESC
                ''')
                
                return [dict(brand) for brand in brands]
                
        except Exception as e:
            logger.error(f"Error retrieving all brands: {e}")
            return []
    
    async def close(self):
        """Close database connections"""
        if self.pool:
            await self.pool.close()