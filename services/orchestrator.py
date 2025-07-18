"""
Main orchestrator service following SOLID principles.
Coordinates all extraction operations with comprehensive error handling and recovery.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import traceback

from models import BrandInsights, BrandContext, PolicyInfo, SocialHandles, ContactDetails, ImportantLinks, AIValidationResult
from services.base import BaseService, OperationResult, ExtractionResult, URLValidator
from services.factory import ServiceFactory, ExtractorFactory, ErrorHandlerFactory, ServiceRegistry
from services.interfaces import (
    IProductExtractor, IBrandContextExtractor, ICurrencyDetector, 
    IAIValidator, ICompetitorAnalyzer, IDataPersistence
)

logger = logging.getLogger(__name__)

class ExtractionMetrics:
    """Tracks metrics for extraction operations"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.operations = {}
        self.errors = []
        self.warnings = []
    
    def record_operation(self, operation: str, duration: float, success: bool, details: Dict[str, Any] = None):
        """Record an operation result"""
        self.operations[operation] = {
            'duration': duration,
            'success': success,
            'details': details or {},
            'timestamp': datetime.now()
        }
    
    def add_error(self, error: str, operation: str = None):
        """Add an error to the metrics"""
        self.errors.append({
            'error': error,
            'operation': operation,
            'timestamp': datetime.now()
        })
    
    def add_warning(self, warning: str, operation: str = None):
        """Add a warning to the metrics"""
        self.warnings.append({
            'warning': warning,
            'operation': operation,
            'timestamp': datetime.now()
        })
    
    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        total_duration = (datetime.now() - self.start_time).total_seconds()
        successful_ops = sum(1 for op in self.operations.values() if op['success'])
        total_ops = len(self.operations)
        
        return {
            'total_duration': total_duration,
            'total_operations': total_ops,
            'successful_operations': successful_ops,
            'success_rate': successful_ops / total_ops if total_ops > 0 else 0,
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
            'operations': self.operations
        }

class ShopifyInsightsOrchestrator(BaseService):
    """
    Main orchestrator for Shopify insights extraction.
    Follows Single Responsibility Principle by coordinating without doing extraction itself.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__()
        self.config = ServiceRegistry.get_config()
        if config:
            self.config.update(config)
        
        self.service_factory = ServiceFactory(self.config)
        self.extractor_factory = ExtractorFactory(self.config)
        self.retry_handler = ErrorHandlerFactory.create_retry_handler(
            max_retries=self.config.get('max_retries', 3)
        )
        self.circuit_breaker = ErrorHandlerFactory.create_circuit_breaker(
            failure_threshold=self.config.get('circuit_breaker_threshold', 5)
        )
        
        # Service instances
        self.currency_detector: Optional[ICurrencyDetector] = None
        self.ai_validator: Optional[IAIValidator] = None
        self.competitor_analyzer: Optional[ICompetitorAnalyzer] = None
        self.database_service: Optional[IDataPersistence] = None
        
        # Extractors
        self.product_extractor: Optional[IProductExtractor] = None
        self.brand_context_extractor: Optional[IBrandContextExtractor] = None
        
        self.metrics = ExtractionMetrics()
    
    async def _initialize_internal(self):
        """Initialize all services and extractors"""
        try:
            # Initialize services
            self.currency_detector = await self.service_factory.create_currency_detector()
            self.ai_validator = await self.service_factory.create_ai_validator()
            self.competitor_analyzer = await self.service_factory.create_competitor_analyzer()
            self.database_service = await self.service_factory.create_database_service()
            
            # Initialize extractors with dependencies
            self.product_extractor = self.extractor_factory.create_product_extractor(
                currency_detector=self.currency_detector
            )
            self.brand_context_extractor = self.extractor_factory.create_brand_context_extractor()
            
            self.logger.info("Orchestrator initialized successfully with all available services")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize orchestrator: {e}")
            raise
    
    async def extract_insights(self, url: str) -> OperationResult:
        """
        Main entry point for extracting insights from a Shopify store.
        Implements comprehensive error handling and recovery strategies.
        """
        start_time = datetime.now()
        
        try:
            # Validate URL first
            url_validation = URLValidator.validate_url(url)
            if not url_validation.is_success:
                return OperationResult(
                    status=ExtractionResult.INVALID_INPUT,
                    error_message=f"Invalid URL: {url_validation.error_message}"
                )
            
            normalized_url = url_validation.data
            self.logger.info(f"Starting extraction for: {normalized_url}")
            
            # Initialize insights object
            insights = BrandInsights(
                website_url=normalized_url,
                brand_context=BrandContext(),
                policies=PolicyInfo(),
                social_handles=SocialHandles(),
                contact_details=ContactDetails(),
                important_links=ImportantLinks(),
                extraction_timestamp=start_time
            )
            
            # Fetch initial HTML content
            html_result = await self._fetch_homepage_content(normalized_url)
            if not html_result.is_success:
                return OperationResult(
                    status=ExtractionResult.FAILURE,
                    error_message=f"Failed to fetch homepage: {html_result.error_message}"
                )
            
            html_content = html_result.data
            
            # Run parallel extraction operations
            extraction_results = await self._run_parallel_extractions(normalized_url, html_content, insights)
            
            # Process extraction results
            await self._process_extraction_results(extraction_results, insights)
            
            # Run AI validation if available
            if self.ai_validator:
                ai_result = await self._run_ai_validation(normalized_url, insights, html_content)
                if ai_result.is_success:
                    insights.ai_validation = ai_result.data
                else:
                    self.metrics.add_warning(f"AI validation failed: {ai_result.error_message}", "ai_validation")
            
            # Run competitor analysis if available
            if self.competitor_analyzer:
                competitor_result = await self._run_competitor_analysis(normalized_url, insights.brand_context)
                if competitor_result.is_success:
                    insights.competitor_analysis = competitor_result.data
                else:
                    self.metrics.add_warning(f"Competitor analysis failed: {competitor_result.error_message}", "competitor_analysis")
            
            # Save to database if available
            if self.database_service:
                db_result = await self._save_to_database(insights)
                if not db_result.is_success:
                    self.metrics.add_warning(f"Database save failed: {db_result.error_message}", "database_save")
            
            # Finalize insights
            self._finalize_insights(insights)
            
            duration = (datetime.now() - start_time).total_seconds()
            self.metrics.record_operation("total_extraction", duration, True, {"url": normalized_url})
            
            self.logger.info(f"Successfully extracted insights for {normalized_url} in {duration:.2f}s")
            
            return OperationResult(
                status=ExtractionResult.SUCCESS,
                data=insights,
                metadata=self.metrics.get_summary()
            )
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self.metrics.record_operation("total_extraction", duration, False, {"error": str(e)})
            self.metrics.add_error(str(e), "total_extraction")
            
            self.logger.error(f"Extraction failed for {url}: {e}")
            self.logger.error(traceback.format_exc())
            
            return OperationResult(
                status=ExtractionResult.FAILURE,
                error_message=f"Extraction failed: {str(e)}",
                metadata=self.metrics.get_summary()
            )
    
    async def _fetch_homepage_content(self, url: str) -> OperationResult:
        """Fetch homepage HTML content with error handling"""
        try:
            network_handler = ServiceRegistry.get_network_handler()
            result = network_handler.get(url)
            
            if result.is_success:
                html_content = result.data.text
                return OperationResult(
                    status=ExtractionResult.SUCCESS,
                    data=html_content,
                    metadata={
                        'content_length': len(html_content),
                        'status_code': result.metadata.get('status_code')
                    }
                )
            else:
                return result
                
        except Exception as e:
            return OperationResult(
                status=ExtractionResult.FAILURE,
                error_message=f"Failed to fetch homepage: {str(e)}"
            )
    
    async def _run_parallel_extractions(self, url: str, html_content: str, insights: BrandInsights) -> Dict[str, OperationResult]:
        """Run all extraction operations in parallel"""
        extraction_tasks = {}
        
        # Product extraction
        if self.product_extractor:
            extraction_tasks['products'] = self._extract_products_with_retry(url)
            extraction_tasks['hero_products'] = self._extract_hero_products_with_retry(url, html_content)
        
        # Brand context extraction
        if self.brand_context_extractor:
            extraction_tasks['brand_context'] = self._extract_brand_context_with_retry(url, html_content)
        
        # Currency detection
        if self.currency_detector:
            extraction_tasks['currency'] = self._detect_currency_with_retry(url, html_content)
        
        # Additional extractors would be added here (FAQs, policies, social handles, etc.)
        
        # Run all tasks concurrently
        try:
            results = await asyncio.gather(
                *[asyncio.create_task(task, name=name) for name, task in extraction_tasks.items()],
                return_exceptions=True
            )
            
            # Map results back to task names
            extraction_results = {}
            for i, (task_name, _) in enumerate(extraction_tasks.items()):
                result = results[i]
                if isinstance(result, Exception):
                    extraction_results[task_name] = OperationResult(
                        status=ExtractionResult.FAILURE,
                        error_message=f"Task failed with exception: {str(result)}"
                    )
                else:
                    extraction_results[task_name] = result
            
            return extraction_results
            
        except Exception as e:
            self.logger.error(f"Parallel extraction failed: {e}")
            # Return partial results if some tasks completed
            return {name: OperationResult(
                status=ExtractionResult.FAILURE,
                error_message=f"Parallel execution failed: {str(e)}"
            ) for name in extraction_tasks.keys()}
    
    async def _extract_products_with_retry(self, url: str) -> OperationResult:
        """Extract products with retry logic"""
        start_time = datetime.now()
        try:
            result = await self.retry_handler(self.product_extractor.extract_products, url)
            duration = (datetime.now() - start_time).total_seconds()
            self.metrics.record_operation("product_extraction", duration, result.is_success)
            return result
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self.metrics.record_operation("product_extraction", duration, False, {"error": str(e)})
            self.metrics.add_error(str(e), "product_extraction")
            return OperationResult(
                status=ExtractionResult.FAILURE,
                error_message=f"Product extraction failed: {str(e)}"
            )
    
    async def _extract_hero_products_with_retry(self, url: str, html_content: str) -> OperationResult:
        """Extract hero products with retry logic"""
        start_time = datetime.now()
        try:
            result = await self.retry_handler(self.product_extractor.extract_hero_products, url, html_content)
            duration = (datetime.now() - start_time).total_seconds()
            self.metrics.record_operation("hero_product_extraction", duration, result.is_success)
            return result
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self.metrics.record_operation("hero_product_extraction", duration, False, {"error": str(e)})
            self.metrics.add_error(str(e), "hero_product_extraction")
            return OperationResult(
                status=ExtractionResult.FAILURE,
                error_message=f"Hero product extraction failed: {str(e)}"
            )
    
    async def _extract_brand_context_with_retry(self, url: str, html_content: str) -> OperationResult:
        """Extract brand context with retry logic"""
        start_time = datetime.now()
        try:
            result = await self.retry_handler(self.brand_context_extractor.extract_brand_context, url, html_content)
            duration = (datetime.now() - start_time).total_seconds()
            self.metrics.record_operation("brand_context_extraction", duration, result.is_success)
            return result
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self.metrics.record_operation("brand_context_extraction", duration, False, {"error": str(e)})
            self.metrics.add_error(str(e), "brand_context_extraction")
            return OperationResult(
                status=ExtractionResult.FAILURE,
                error_message=f"Brand context extraction failed: {str(e)}"
            )
    
    async def _detect_currency_with_retry(self, url: str, html_content: str) -> OperationResult:
        """Detect currency with retry logic"""
        start_time = datetime.now()
        try:
            result = await self.retry_handler(self.currency_detector.detect_currency, url, html_content)
            duration = (datetime.now() - start_time).total_seconds()
            self.metrics.record_operation("currency_detection", duration, result.is_success)
            return result
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self.metrics.record_operation("currency_detection", duration, False, {"error": str(e)})
            self.metrics.add_error(str(e), "currency_detection")
            return OperationResult(
                status=ExtractionResult.FAILURE,
                error_message=f"Currency detection failed: {str(e)}"
            )
    
    async def _process_extraction_results(self, extraction_results: Dict[str, OperationResult], insights: BrandInsights):
        """Process and integrate extraction results into insights object"""
        errors = []
        
        # Process products
        if 'products' in extraction_results:
            result = extraction_results['products']
            if result.is_success and result.data:
                insights.product_catalog = result.data
                insights.total_products_found = len(result.data)
            elif result.warnings:
                errors.extend(result.warnings)
        
        # Process hero products
        if 'hero_products' in extraction_results:
            result = extraction_results['hero_products']
            if result.is_success and result.data:
                insights.hero_products = result.data
            elif result.warnings:
                errors.extend(result.warnings)
        
        # Process brand context
        if 'brand_context' in extraction_results:
            result = extraction_results['brand_context']
            if result.is_success and result.data:
                insights.brand_context = result.data
            elif result.warnings:
                errors.extend(result.warnings)
        
        # Process currency information
        if 'currency' in extraction_results:
            result = extraction_results['currency']
            if result.is_success and result.data:
                currency_data = result.data
                insights.detected_currency = currency_data.get('currency')
                insights.currency_symbol = currency_data.get('currency_symbol')
            elif result.warnings:
                errors.extend(result.warnings)
        
        # Set errors in insights
        if errors:
            insights.errors = errors
    
    async def _run_ai_validation(self, url: str, insights: BrandInsights, html_content: str) -> OperationResult:
        """Run AI validation if available"""
        try:
            start_time = datetime.now()
            result = await self.ai_validator.comprehensive_validation(url, insights)
            duration = (datetime.now() - start_time).total_seconds()
            self.metrics.record_operation("ai_validation", duration, result.is_success)
            return result
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self.metrics.record_operation("ai_validation", duration, False, {"error": str(e)})
            return OperationResult(
                status=ExtractionResult.FAILURE,
                error_message=f"AI validation failed: {str(e)}"
            )
    
    async def _run_competitor_analysis(self, url: str, brand_context: BrandContext) -> OperationResult:
        """Run competitor analysis if available"""
        try:
            start_time = datetime.now()
            result = await self.competitor_analyzer.analyze_competitors(url, brand_context)
            duration = (datetime.now() - start_time).total_seconds()
            self.metrics.record_operation("competitor_analysis", duration, result.is_success)
            return result
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self.metrics.record_operation("competitor_analysis", duration, False, {"error": str(e)}")
            return OperationResult(
                status=ExtractionResult.FAILURE,
                error_message=f"Competitor analysis failed: {str(e)}"
            )
    
    async def _save_to_database(self, insights: BrandInsights) -> OperationResult:
        """Save insights to database if available"""
        try:
            start_time = datetime.now()
            result = await self.database_service.save_insights(insights)
            duration = (datetime.now() - start_time).total_seconds()
            self.metrics.record_operation("database_save", duration, result.is_success)
            return result
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self.metrics.record_operation("database_save", duration, False, {"error": str(e)})
            return OperationResult(
                status=ExtractionResult.FAILURE,
                error_message=f"Database save failed: {str(e)}"
            )
    
    def _finalize_insights(self, insights: BrandInsights):
        """Finalize insights object with success status"""
        # Set extraction success based on whether we got meaningful data
        has_products = len(insights.product_catalog) > 0 or len(insights.hero_products) > 0
        has_brand_info = bool(insights.brand_context.brand_name)
        
        insights.extraction_success = has_products or has_brand_info
        
        # Add any final validation errors
        if not insights.extraction_success:
            insights.errors.append("No meaningful data could be extracted from the store")
    
    async def _cleanup_internal(self):
        """Cleanup orchestrator resources"""
        try:
            if self.service_factory:
                await self.service_factory.cleanup_all_services()
        except Exception as e:
            self.logger.error(f"Error during orchestrator cleanup: {e}")

# Adapter for backward compatibility with existing API
class LegacyScraperAdapter:
    """
    Adapter pattern implementation to maintain backward compatibility
    with the existing API while using the new orchestrator internally.
    """
    
    def __init__(self):
        self.orchestrator = None
    
    async def extract_all_insights(self, url: str) -> BrandInsights:
        """Legacy method signature that delegates to new orchestrator"""
        try:
            # For now, fall back to the original scraper to maintain compatibility
            # while we fix the new architecture issues
            from services.scraper import ShopifyScraperService
            legacy_scraper = ShopifyScraperService()
            return await legacy_scraper.extract_all_insights(url)
            
        except Exception as e:
            logger.error(f"Legacy adapter failed: {e}")
            # Return error insights object
            insights = BrandInsights(
                website_url=url,
                brand_context=BrandContext(),
                policies=PolicyInfo(),
                social_handles=SocialHandles(),
                contact_details=ContactDetails(),
                important_links=ImportantLinks(),
                extraction_success=False,
                errors=[f"Extraction failed: {str(e)}"]
            )
            return insights
                
        except Exception as e:
            logger.error(f"Legacy adapter failed: {e}")
            # Return error insights object
            insights = BrandInsights(
                website_url=url,
                brand_context=BrandContext(),
                policies=PolicyInfo(),
                social_handles=SocialHandles(),
                contact_details=ContactDetails(),
                important_links=ImportantLinks(),
                extraction_success=False,
                errors=[f"Extraction failed: {str(e)}"]
            )
            return insights
    
    def _normalize_url(self, url: str) -> str:
        """Legacy URL normalization method"""
        result = URLValidator.validate_url(url)
        return result.data if result.is_success else url