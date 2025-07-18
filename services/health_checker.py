"""
Health checking service for comprehensive system monitoring.
Implements dependency validation and service health assessment.
"""

import asyncio
import logging
import os
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

import requests
from services.base import BaseService, OperationResult, ExtractionResult
from services.interfaces import IHealthChecker

logger = logging.getLogger(__name__)

class ServiceStatus(Enum):
    """Service status enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DISABLED = "disabled"
    UNKNOWN = "unknown"

@dataclass
class HealthCheck:
    """Individual health check result"""
    service_name: str
    status: ServiceStatus
    response_time: Optional[float] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class SystemHealthChecker(BaseService, IHealthChecker):
    """Comprehensive system health checker"""
    
    def __init__(self):
        super().__init__()
        self.health_checks: List[HealthCheck] = []
        self.last_check_time: Optional[float] = None
    
    async def _initialize_internal(self):
        """Initialize health checker"""
        self.logger.info("Health checker initialized")
    
    async def check_health(self) -> OperationResult:
        """Perform comprehensive health check"""
        try:
            start_time = time.time()
            self.health_checks.clear()
            
            # Run all health checks
            await asyncio.gather(
                self._check_database_health(),
                self._check_ai_service_health(),
                self._check_network_connectivity(),
                self._check_environment_variables(),
                self._check_memory_usage(),
                return_exceptions=True
            )
            
            # Calculate overall health
            overall_status = self._calculate_overall_health()
            check_duration = time.time() - start_time
            self.last_check_time = start_time
            
            health_report = {
                "overall_status": overall_status.value,
                "check_timestamp": start_time,
                "check_duration": check_duration,
                "services": [
                    {
                        "name": check.service_name,
                        "status": check.status.value,
                        "response_time": check.response_time,
                        "error": check.error_message,
                        "metadata": check.metadata
                    }
                    for check in self.health_checks
                ]
            }
            
            return OperationResult(
                status=ExtractionResult.SUCCESS,
                data=health_report,
                metadata={"services_checked": len(self.health_checks)}
            )
            
        except Exception as e:
            return OperationResult(
                status=ExtractionResult.FAILURE,
                error_message=f"Health check failed: {str(e)}"
            )
    
    async def check_dependencies(self) -> OperationResult:
        """Check health of external dependencies"""
        try:
            dependency_checks = []
            
            # Check database connection
            db_check = await self._check_database_connection()
            dependency_checks.append(db_check)
            
            # Check AI service availability
            ai_check = await self._check_ai_service_availability()
            dependency_checks.append(ai_check)
            
            # Check external network services
            network_check = await self._check_external_services()
            dependency_checks.append(network_check)
            
            dependencies_status = {
                check.service_name: {
                    "status": check.status.value,
                    "response_time": check.response_time,
                    "error": check.error_message,
                    "metadata": check.metadata
                }
                for check in dependency_checks
            }
            
            return OperationResult(
                status=ExtractionResult.SUCCESS,
                data=dependencies_status
            )
            
        except Exception as e:
            return OperationResult(
                status=ExtractionResult.FAILURE,
                error_message=f"Dependency check failed: {str(e)}"
            )
    
    async def _check_database_health(self):
        """Check database connectivity and performance"""
        start_time = time.time()
        
        try:
            if not os.getenv('DATABASE_URL'):
                self.health_checks.append(HealthCheck(
                    service_name="database",
                    status=ServiceStatus.DISABLED,
                    metadata={"reason": "No DATABASE_URL configured"}
                ))
                return
            
            # Try to connect to database
            import asyncpg
            
            try:
                conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
                
                # Test query
                result = await conn.fetchval('SELECT 1')
                await conn.close()
                
                response_time = time.time() - start_time
                
                if response_time < 1.0:
                    status = ServiceStatus.HEALTHY
                elif response_time < 3.0:
                    status = ServiceStatus.DEGRADED
                else:
                    status = ServiceStatus.UNHEALTHY
                
                self.health_checks.append(HealthCheck(
                    service_name="database",
                    status=status,
                    response_time=response_time,
                    metadata={"query_result": result}
                ))
                
            except Exception as e:
                self.health_checks.append(HealthCheck(
                    service_name="database",
                    status=ServiceStatus.UNHEALTHY,
                    response_time=time.time() - start_time,
                    error_message=str(e)
                ))
                
        except ImportError:
            self.health_checks.append(HealthCheck(
                service_name="database",
                status=ServiceStatus.DISABLED,
                metadata={"reason": "asyncpg not available"}
            ))
    
    async def _check_ai_service_health(self):
        """Check AI service (Gemini) availability"""
        try:
            api_key = os.getenv('GEMINI_API_KEY')
            
            if not api_key:
                self.health_checks.append(HealthCheck(
                    service_name="ai_service",
                    status=ServiceStatus.DISABLED,
                    metadata={"reason": "No GEMINI_API_KEY configured"}
                ))
                return
            
            start_time = time.time()
            
            try:
                import google.genai as genai
                
                client = genai.Client(api_key=api_key)
                
                # Simple test request
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents="Test"
                )
                
                response_time = time.time() - start_time
                
                if response_time < 2.0:
                    status = ServiceStatus.HEALTHY
                elif response_time < 5.0:
                    status = ServiceStatus.DEGRADED
                else:
                    status = ServiceStatus.UNHEALTHY
                
                self.health_checks.append(HealthCheck(
                    service_name="ai_service",
                    status=status,
                    response_time=response_time,
                    metadata={"api_working": True}
                ))
                
            except Exception as e:
                self.health_checks.append(HealthCheck(
                    service_name="ai_service",
                    status=ServiceStatus.UNHEALTHY,
                    response_time=time.time() - start_time,
                    error_message=str(e)
                ))
                
        except ImportError:
            self.health_checks.append(HealthCheck(
                service_name="ai_service",
                status=ServiceStatus.DISABLED,
                metadata={"reason": "google-genai not available"}
            ))
    
    async def _check_network_connectivity(self):
        """Check basic network connectivity"""
        start_time = time.time()
        
        try:
            # Test basic HTTP connectivity
            response = requests.get(
                'https://httpbin.org/status/200',
                timeout=5
            )
            
            response_time = time.time() - start_time
            
            if response.status_code == 200 and response_time < 2.0:
                status = ServiceStatus.HEALTHY
            elif response.status_code == 200 and response_time < 5.0:
                status = ServiceStatus.DEGRADED
            else:
                status = ServiceStatus.UNHEALTHY
            
            self.health_checks.append(HealthCheck(
                service_name="network",
                status=status,
                response_time=response_time,
                metadata={"status_code": response.status_code}
            ))
            
        except Exception as e:
            self.health_checks.append(HealthCheck(
                service_name="network",
                status=ServiceStatus.UNHEALTHY,
                response_time=time.time() - start_time,
                error_message=str(e)
            ))
    
    async def _check_environment_variables(self):
        """Check required environment variables"""
        required_vars = ['DATABASE_URL', 'PGHOST', 'PGPORT', 'PGUSER', 'PGPASSWORD', 'PGDATABASE']
        optional_vars = ['GEMINI_API_KEY']
        
        missing_required = []
        missing_optional = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing_required.append(var)
        
        for var in optional_vars:
            if not os.getenv(var):
                missing_optional.append(var)
        
        if missing_required:
            status = ServiceStatus.UNHEALTHY
            error_msg = f"Missing required environment variables: {', '.join(missing_required)}"
        elif missing_optional:
            status = ServiceStatus.DEGRADED
            error_msg = f"Missing optional environment variables: {', '.join(missing_optional)}"
        else:
            status = ServiceStatus.HEALTHY
            error_msg = None
        
        self.health_checks.append(HealthCheck(
            service_name="environment",
            status=status,
            error_message=error_msg,
            metadata={
                "required_vars_present": len(required_vars) - len(missing_required),
                "optional_vars_present": len(optional_vars) - len(missing_optional),
                "missing_required": missing_required,
                "missing_optional": missing_optional
            }
        ))
    
    async def _check_memory_usage(self):
        """Check memory usage"""
        try:
            import psutil
            
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            
            if memory_usage < 70:
                status = ServiceStatus.HEALTHY
            elif memory_usage < 85:
                status = ServiceStatus.DEGRADED
            else:
                status = ServiceStatus.UNHEALTHY
            
            self.health_checks.append(HealthCheck(
                service_name="memory",
                status=status,
                metadata={
                    "usage_percent": memory_usage,
                    "available_gb": round(memory.available / (1024**3), 2),
                    "total_gb": round(memory.total / (1024**3), 2)
                }
            ))
            
        except ImportError:
            self.health_checks.append(HealthCheck(
                service_name="memory",
                status=ServiceStatus.UNKNOWN,
                metadata={"reason": "psutil not available"}
            ))
        except Exception as e:
            self.health_checks.append(HealthCheck(
                service_name="memory",
                status=ServiceStatus.UNKNOWN,
                error_message=str(e)
            ))
    
    async def _check_database_connection(self) -> HealthCheck:
        """Check database connection specifically"""
        start_time = time.time()
        
        if not os.getenv('DATABASE_URL'):
            return HealthCheck(
                service_name="database_connection",
                status=ServiceStatus.DISABLED,
                metadata={"reason": "No DATABASE_URL"}
            )
        
        try:
            import asyncpg
            
            conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
            await conn.fetchval('SELECT 1')
            await conn.close()
            
            return HealthCheck(
                service_name="database_connection",
                status=ServiceStatus.HEALTHY,
                response_time=time.time() - start_time
            )
            
        except Exception as e:
            return HealthCheck(
                service_name="database_connection",
                status=ServiceStatus.UNHEALTHY,
                response_time=time.time() - start_time,
                error_message=str(e)
            )
    
    async def _check_ai_service_availability(self) -> HealthCheck:
        """Check AI service availability specifically"""
        if not os.getenv('GEMINI_API_KEY'):
            return HealthCheck(
                service_name="ai_availability",
                status=ServiceStatus.DISABLED,
                metadata={"reason": "No GEMINI_API_KEY"}
            )
        
        start_time = time.time()
        
        try:
            import google.genai as genai
            
            client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
            
            # Test with minimal request
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents="Hello"
            )
            
            return HealthCheck(
                service_name="ai_availability",
                status=ServiceStatus.HEALTHY,
                response_time=time.time() - start_time,
                metadata={"response_length": len(response.text) if response.text else 0}
            )
            
        except Exception as e:
            return HealthCheck(
                service_name="ai_availability",
                status=ServiceStatus.UNHEALTHY,
                response_time=time.time() - start_time,
                error_message=str(e)
            )
    
    async def _check_external_services(self) -> HealthCheck:
        """Check external service connectivity"""
        start_time = time.time()
        
        test_urls = [
            'https://httpbin.org/status/200',
            'https://www.google.com',
        ]
        
        successful_requests = 0
        total_requests = len(test_urls)
        
        for url in test_urls:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    successful_requests += 1
            except Exception:
                pass
        
        success_rate = successful_requests / total_requests
        response_time = time.time() - start_time
        
        if success_rate >= 0.8:
            status = ServiceStatus.HEALTHY
        elif success_rate >= 0.5:
            status = ServiceStatus.DEGRADED
        else:
            status = ServiceStatus.UNHEALTHY
        
        return HealthCheck(
            service_name="external_services",
            status=status,
            response_time=response_time,
            metadata={
                "success_rate": success_rate,
                "successful_requests": successful_requests,
                "total_requests": total_requests
            }
        )
    
    def _calculate_overall_health(self) -> ServiceStatus:
        """Calculate overall system health based on individual checks"""
        if not self.health_checks:
            return ServiceStatus.UNKNOWN
        
        unhealthy_count = sum(1 for check in self.health_checks if check.status == ServiceStatus.UNHEALTHY)
        degraded_count = sum(1 for check in self.health_checks if check.status == ServiceStatus.DEGRADED)
        healthy_count = sum(1 for check in self.health_checks if check.status == ServiceStatus.HEALTHY)
        
        total_active = len([check for check in self.health_checks if check.status != ServiceStatus.DISABLED])
        
        if total_active == 0:
            return ServiceStatus.UNKNOWN
        
        unhealthy_ratio = unhealthy_count / total_active
        degraded_ratio = degraded_count / total_active
        
        if unhealthy_ratio > 0.5:
            return ServiceStatus.UNHEALTHY
        elif unhealthy_ratio > 0.2 or degraded_ratio > 0.5:
            return ServiceStatus.DEGRADED
        else:
            return ServiceStatus.HEALTHY
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get a summary of the last health check"""
        if not self.health_checks:
            return {"status": "no_data", "message": "No health checks performed yet"}
        
        overall_status = self._calculate_overall_health()
        
        return {
            "overall_status": overall_status.value,
            "last_check": self.last_check_time,
            "services_count": len(self.health_checks),
            "healthy_services": len([c for c in self.health_checks if c.status == ServiceStatus.HEALTHY]),
            "degraded_services": len([c for c in self.health_checks if c.status == ServiceStatus.DEGRADED]),
            "unhealthy_services": len([c for c in self.health_checks if c.status == ServiceStatus.UNHEALTHY]),
            "disabled_services": len([c for c in self.health_checks if c.status == ServiceStatus.DISABLED])
        }