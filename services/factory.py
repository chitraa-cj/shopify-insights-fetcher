"""
Factory classes implementing the Factory pattern for creating services and extractors.
Follows Dependency Inversion Principle by depending on abstractions.
"""

from typing import Dict, Type, Any, Optional
import os
import logging

from services.base import BaseService, NetworkHandler, ConfigurationManager, OperationResult, ExtractionResult
from services.interfaces import (
    IProductExtractor, IBrandContextExtractor, IPolicyExtractor, IFAQExtractor,
    ISocialMediaExtractor, IContactExtractor, ICurrencyDetector, IAIValidator,
    ICompetitorAnalyzer, IDataPersistence, IHealthChecker
)
from services.extractors import ProductExtractor, BrandContextExtractor, EmailExtractor, PhoneExtractor, URLExtractor

logger = logging.getLogger(__name__)

class ServiceRegistry:
    """Registry for managing service instances following Singleton pattern where appropriate"""
    
    _instances: Dict[str, Any] = {}
    _network_handler: Optional[NetworkHandler] = None
    _config: Optional[ConfigurationManager] = None
    
    @classmethod
    def get_network_handler(cls) -> NetworkHandler:
        """Get shared network handler instance"""
        if cls._network_handler is None:
            config = cls.get_config()
            cls._network_handler = NetworkHandler(
                timeout=config.get('timeout', 30),
                max_retries=config.get('max_retries', 3),
                backoff_factor=config.get('backoff_factor', 0.3)
            )
        return cls._network_handler
    
    @classmethod
    def get_config(cls) -> ConfigurationManager:
        """Get configuration manager instance"""
        if cls._config is None:
            # Load configuration from environment or defaults
            config_dict = {
                'timeout': int(os.getenv('REQUEST_TIMEOUT', 30)),
                'max_retries': int(os.getenv('MAX_RETRIES', 3)),
                'rate_limit_requests': int(os.getenv('RATE_LIMIT_REQUESTS', 10)),
                'rate_limit_window': int(os.getenv('RATE_LIMIT_WINDOW', 60)),
                'max_products_per_page': int(os.getenv('MAX_PRODUCTS_PER_PAGE', 250)),
                'max_pages': int(os.getenv('MAX_PAGES', 10)),
                'ai_enabled': os.getenv('GEMINI_API_KEY') is not None,
                'database_enabled': os.getenv('DATABASE_URL') is not None
            }
            cls._config = ConfigurationManager(config_dict)
        return cls._config
    
    @classmethod
    def register_service(cls, name: str, instance: Any):
        """Register a service instance"""
        cls._instances[name] = instance
        logger.debug(f"Registered service: {name}")
    
    @classmethod
    def get_service(cls, name: str) -> Optional[Any]:
        """Get a registered service instance"""
        return cls._instances.get(name)
    
    @classmethod
    def clear_registry(cls):
        """Clear all registered services (useful for testing)"""
        cls._instances.clear()
        cls._network_handler = None
        cls._config = None

class ExtractorFactory:
    """Factory for creating extractor instances with proper dependency injection"""
    
    def __init__(self, config: Optional[ConfigurationManager] = None):
        self.config = config or ServiceRegistry.get_config()
        self.network_handler = ServiceRegistry.get_network_handler()
        self._extractors: Dict[str, Any] = {}
    
    def create_product_extractor(self, currency_detector: Optional[ICurrencyDetector] = None) -> IProductExtractor:
        """Create product extractor with dependencies"""
        if 'product' not in self._extractors:
            self._extractors['product'] = ProductExtractor(
                network_handler=self.network_handler,
                currency_detector=currency_detector
            )
        return self._extractors['product']
    
    def create_brand_context_extractor(self) -> IBrandContextExtractor:
        """Create brand context extractor"""
        if 'brand_context' not in self._extractors:
            self._extractors['brand_context'] = BrandContextExtractor(
                network_handler=self.network_handler
            )
        return self._extractors['brand_context']
    
    def create_email_extractor(self) -> EmailExtractor:
        """Create email extractor utility"""
        if 'email' not in self._extractors:
            self._extractors['email'] = EmailExtractor()
        return self._extractors['email']
    
    def create_phone_extractor(self) -> PhoneExtractor:
        """Create phone extractor utility"""
        if 'phone' not in self._extractors:
            self._extractors['phone'] = PhoneExtractor()
        return self._extractors['phone']
    
    def create_url_extractor(self) -> URLExtractor:
        """Create URL extractor utility"""
        if 'url' not in self._extractors:
            self._extractors['url'] = URLExtractor()
        return self._extractors['url']
    
    def get_all_extractors(self) -> Dict[str, Any]:
        """Get all available extractors"""
        return {
            'product': self.create_product_extractor(),
            'brand_context': self.create_brand_context_extractor(),
            'email': self.create_email_extractor(),
            'phone': self.create_phone_extractor(),
            'url': self.create_url_extractor()
        }

class ServiceFactory:
    """Main factory for creating all types of services"""
    
    def __init__(self, config: Optional[ConfigurationManager] = None):
        self.config = config or ServiceRegistry.get_config()
        self.extractor_factory = ExtractorFactory(self.config)
        self._services: Dict[str, Any] = {}
    
    async def create_currency_detector(self) -> Optional[ICurrencyDetector]:
        """Create currency detection service"""
        try:
            # Import here to avoid circular dependencies
            from services.currency_service import CurrencyDetectionService
            
            if 'currency_detector' not in self._services:
                service = CurrencyDetectionService()
                await service.initialize()
                self._services['currency_detector'] = service
            
            return self._services['currency_detector']
        except ImportError:
            logger.warning("Currency detection service not available")
            return None
        except Exception as e:
            logger.error(f"Failed to create currency detector: {e}")
            return None
    
    async def create_ai_validator(self) -> Optional[IAIValidator]:
        """Create AI validation service if available"""
        if not self.config.get('ai_enabled', False):
            logger.info("AI validation disabled - no API key provided")
            return None
        
        try:
            # Import here to avoid circular dependencies
            from services.ai_validator import AIValidatorService
            
            if 'ai_validator' not in self._services:
                service = AIValidatorService(ServiceRegistry.get_network_handler())
                self._services['ai_validator'] = service
            
            return self._services['ai_validator']
        except ImportError:
            logger.warning("AI validation service not available")
            return None
        except Exception as e:
            logger.error(f"Failed to create AI validator: {e}")
            return None
    
    async def create_competitor_analyzer(self) -> Optional[ICompetitorAnalyzer]:
        """Create competitor analysis service"""
        try:
            # Import here to avoid circular dependencies
            from services.competitor_analyzer import CompetitorAnalyzer
            
            if 'competitor_analyzer' not in self._services:
                service = CompetitorAnalyzer()
                self._services['competitor_analyzer'] = service
            
            return self._services['competitor_analyzer']
        except ImportError:
            logger.warning("Competitor analyzer service not available")
            return None
        except Exception as e:
            logger.error(f"Failed to create competitor analyzer: {e}")
            return None
    
    async def create_database_service(self) -> Optional[IDataPersistence]:
        """Create database service if available"""
        if not self.config.get('database_enabled', False):
            logger.info("Database service disabled - no DATABASE_URL provided")
            return None
        
        try:
            # Import here to avoid circular dependencies
            from services.database_service import DatabaseService
            
            if 'database_service' not in self._services:
                service = DatabaseService()
                await service.initialize()
                self._services['database_service'] = service
            
            return self._services['database_service']
        except ImportError:
            logger.warning("Database service not available")
            return None
        except Exception as e:
            logger.error(f"Failed to create database service: {e}")
            return None
    
    async def create_health_checker(self) -> IHealthChecker:
        """Create health checker service"""
        if 'health_checker' not in self._services:
            self._services['health_checker'] = HealthCheckerService(
                network_handler=ServiceRegistry.get_network_handler(),
                config=self.config
            )
        
        return self._services['health_checker']
    
    async def cleanup_all_services(self):
        """Cleanup all created services"""
        for service_name, service in self._services.items():
            try:
                if hasattr(service, 'cleanup'):
                    await service.cleanup()
                logger.debug(f"Cleaned up service: {service_name}")
            except Exception as e:
                logger.error(f"Error cleaning up service {service_name}: {e}")
        
        self._services.clear()

class HealthCheckerService(BaseService, IHealthChecker):
    """Health checker service implementation"""
    
    def __init__(self, network_handler: NetworkHandler, config: ConfigurationManager):
        super().__init__()
        self.network_handler = network_handler
        self.config = config
    
    async def _initialize_internal(self):
        """Initialize health checker"""
        pass  # No special initialization needed
    
    async def check_health(self) -> OperationResult:
        """Check overall service health"""
        try:
            health_status = {
                'status': 'healthy',
                'timestamp': None,  # Would use datetime.now().isoformat()
                'services': {}
            }
            
            # Check dependencies
            deps_result = await self.check_dependencies()
            health_status['services'] = deps_result.data if deps_result.is_success else {}
            
            overall_healthy = all(
                service.get('status') == 'healthy' 
                for service in health_status['services'].values()
            )
            
            if not overall_healthy:
                health_status['status'] = 'degraded'
            
            return OperationResult(
                status=ExtractionResult.SUCCESS,
                data=health_status
            )
            
        except Exception as e:
            return OperationResult(
                status=ExtractionResult.FAILURE,
                error_message=f"Health check failed: {str(e)}"
            )
    
    async def check_dependencies(self) -> OperationResult:
        """Check health of dependencies"""
        try:
            services_status = {}
            
            # Check network connectivity
            test_result = self.network_handler.get('https://httpbin.org/status/200')
            services_status['network'] = {
                'status': 'healthy' if test_result.is_success else 'unhealthy',
                'details': test_result.error_message if not test_result.is_success else 'OK'
            }
            
            # Check AI service availability
            ai_enabled = self.config.get('ai_enabled', False)
            services_status['ai_validation'] = {
                'status': 'healthy' if ai_enabled else 'disabled',
                'details': 'Gemini API key available' if ai_enabled else 'No API key provided'
            }
            
            # Check database availability
            db_enabled = self.config.get('database_enabled', False)
            services_status['database'] = {
                'status': 'healthy' if db_enabled else 'disabled',
                'details': 'Database URL available' if db_enabled else 'No DATABASE_URL provided'
            }
            
            return OperationResult(
                status=ExtractionResult.SUCCESS,
                data=services_status
            )
            
        except Exception as e:
            return OperationResult(
                status=ExtractionResult.FAILURE,
                error_message=f"Dependency check failed: {str(e)}"
            )

class ErrorHandlerFactory:
    """Factory for creating error handlers and recovery strategies"""
    
    @staticmethod
    def create_retry_handler(max_retries: int = 3, backoff_factor: float = 0.3):
        """Create a retry handler for operations"""
        async def retry_handler(operation, *args, **kwargs):
            for attempt in range(max_retries + 1):
                try:
                    result = await operation(*args, **kwargs)
                    if result.is_success or result.is_partial_success:
                        return result
                    
                    if attempt < max_retries:
                        import asyncio
                        wait_time = backoff_factor * (2 ** attempt)
                        await asyncio.sleep(wait_time)
                    
                except Exception as e:
                    if attempt == max_retries:
                        return OperationResult(
                            status=ExtractionResult.FAILURE,
                            error_message=f"Operation failed after {max_retries} retries: {str(e)}"
                        )
                    
                    import asyncio
                    wait_time = backoff_factor * (2 ** attempt)
                    await asyncio.sleep(wait_time)
            
            return OperationResult(
                status=ExtractionResult.FAILURE,
                error_message="Max retries exceeded"
            )
        
        return retry_handler
    
    @staticmethod
    def create_circuit_breaker(failure_threshold: int = 5, reset_timeout: int = 60):
        """Create a circuit breaker for preventing cascading failures"""
        class CircuitBreaker:
            def __init__(self):
                self.failure_count = 0
                self.last_failure_time = 0
                self.state = 'closed'  # closed, open, half-open
            
            async def call(self, operation, *args, **kwargs):
                import time
                
                # Check if circuit should be reset
                if self.state == 'open' and time.time() - self.last_failure_time > reset_timeout:
                    self.state = 'half-open'
                
                # Reject calls if circuit is open
                if self.state == 'open':
                    return OperationResult(
                        status=ExtractionResult.FAILURE,
                        error_message="Circuit breaker is open"
                    )
                
                try:
                    result = await operation(*args, **kwargs)
                    
                    if result.is_success:
                        # Reset circuit breaker on success
                        if self.state == 'half-open':
                            self.state = 'closed'
                            self.failure_count = 0
                        return result
                    else:
                        # Handle failure
                        self.failure_count += 1
                        self.last_failure_time = time.time()
                        
                        if self.failure_count >= failure_threshold:
                            self.state = 'open'
                        
                        return result
                
                except Exception as e:
                    self.failure_count += 1
                    self.last_failure_time = time.time()
                    
                    if self.failure_count >= failure_threshold:
                        self.state = 'open'
                    
                    return OperationResult(
                        status=ExtractionResult.FAILURE,
                        error_message=f"Circuit breaker: {str(e)}"
                    )
        
        return CircuitBreaker()