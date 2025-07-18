#!/usr/bin/env python3
"""
Comprehensive edge case testing for the Shopify Insights Fetcher.
Tests all major failure scenarios and recovery mechanisms.
"""

import asyncio
import json
import logging
import sys
import time
from typing import Dict, Any, List

# Test configuration
TEST_CASES = [
    {
        "name": "Invalid URL - Malformed",
        "url": "not-a-valid-url",
        "expected_status": 401,
        "expected_error": "Website not found or invalid"
    },
    {
        "name": "Invalid URL - Non-existent domain",
        "url": "https://this-domain-does-not-exist-12345.com",
        "expected_status": 401,
        "expected_error": "Website not found or unreachable"
    },
    {
        "name": "Valid URL - 404 Page",
        "url": "https://httpbin.org/status/404",
        "expected_status": 401,
        "expected_error": "Website not found"
    },
    {
        "name": "Valid URL - 403 Forbidden",
        "url": "https://httpbin.org/status/403",
        "expected_status": 401,
        "expected_error": "Access forbidden"
    },
    {
        "name": "Valid URL - 500 Server Error",
        "url": "https://httpbin.org/status/500",
        "expected_status": 500,
        "expected_error": "Server error"
    },
    {
        "name": "Valid URL - Timeout Test",
        "url": "https://httpbin.org/delay/35",  # 35 second delay, should timeout
        "expected_status": 401,
        "expected_error": "timeout"
    },
    {
        "name": "Non-Shopify Store",
        "url": "https://google.com",
        "expected_status": 200,  # Should work but with limited data
        "check_partial": True
    },
    {
        "name": "Valid Shopify Store",
        "url": "https://memy.co.in",
        "expected_status": 200,
        "check_success": True
    }
]

class EdgeCaseTester:
    """Comprehensive edge case testing suite"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.results = []
        self.passed = 0
        self.failed = 0
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    async def run_all_tests(self):
        """Run all edge case tests"""
        self.logger.info("Starting comprehensive edge case testing...")
        self.logger.info(f"Testing against: {self.base_url}")
        
        start_time = time.time()
        
        for i, test_case in enumerate(TEST_CASES, 1):
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"Test {i}/{len(TEST_CASES)}: {test_case['name']}")
            self.logger.info(f"URL: {test_case['url']}")
            self.logger.info(f"{'='*60}")
            
            result = await self.run_single_test(test_case)
            self.results.append(result)
            
            if result['passed']:
                self.passed += 1
                self.logger.info(f"✅ PASSED: {test_case['name']}")
            else:
                self.failed += 1
                self.logger.error(f"❌ FAILED: {test_case['name']}")
                self.logger.error(f"   Expected: {result['expected']}")
                self.logger.error(f"   Actual: {result['actual']}")
            
            # Small delay between tests
            await asyncio.sleep(1)
        
        total_time = time.time() - start_time
        await self.generate_report(total_time)
    
    async def run_single_test(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single test case"""
        import aiohttp
        
        result = {
            'name': test_case['name'],
            'url': test_case['url'],
            'passed': False,
            'expected': '',
            'actual': '',
            'response_time': 0,
            'error_details': ''
        }
        
        start_time = time.time()
        
        try:
            timeout = aiohttp.ClientTimeout(total=40)  # 40 second timeout
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                payload = {"website_url": test_case['url']}
                
                async with session.post(
                    f"{self.base_url}/extract-insights",
                    json=payload,
                    headers={'Content-Type': 'application/json'}
                ) as response:
                    
                    response_time = time.time() - start_time
                    result['response_time'] = response_time
                    
                    status_code = response.status
                    
                    try:
                        response_data = await response.json()
                    except Exception:
                        response_data = {"detail": await response.text()}
                    
                    # Check expected status code
                    expected_status = test_case.get('expected_status', 200)
                    result['expected'] = f"Status {expected_status}"
                    result['actual'] = f"Status {status_code}"
                    
                    if status_code == expected_status:
                        # Check additional conditions
                        if test_case.get('check_success', False):
                            # For successful cases, check if we got meaningful data
                            if (status_code == 200 and 
                                'brand_context' in response_data and
                                ('product_catalog' in response_data or 'hero_products' in response_data)):
                                result['passed'] = True
                                result['actual'] += " with valid data"
                            else:
                                result['actual'] += " but missing expected data"
                                result['error_details'] = "Response missing required fields"
                        
                        elif test_case.get('check_partial', False):
                            # For partial cases, just check that we get a response
                            if status_code == 200:
                                result['passed'] = True
                                result['actual'] += " (partial success expected)"
                            else:
                                result['error_details'] = "Expected partial success but got error"
                        
                        else:
                            # For error cases, check error message contains expected text
                            expected_error = test_case.get('expected_error', '')
                            error_message = response_data.get('detail', '')
                            
                            if expected_error.lower() in error_message.lower():
                                result['passed'] = True
                                result['actual'] += f" with correct error: {error_message}"
                            else:
                                result['actual'] += f" but wrong error: {error_message}"
                                result['error_details'] = f"Expected error containing '{expected_error}'"
                    
                    else:
                        result['error_details'] = f"Status code mismatch. Response: {response_data}"
        
        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            result['response_time'] = response_time
            result['actual'] = "Request timeout"
            
            # Check if timeout was expected
            if 'timeout' in test_case.get('expected_error', '').lower():
                result['passed'] = True
                result['actual'] += " (expected)"
            else:
                result['error_details'] = "Unexpected timeout"
        
        except Exception as e:
            response_time = time.time() - start_time
            result['response_time'] = response_time
            result['actual'] = f"Exception: {str(e)}"
            result['error_details'] = str(e)
        
        return result
    
    async def generate_report(self, total_time: float):
        """Generate comprehensive test report"""
        self.logger.info(f"\n{'='*80}")
        self.logger.info("COMPREHENSIVE EDGE CASE TEST REPORT")
        self.logger.info(f"{'='*80}")
        
        self.logger.info(f"Total Tests: {len(self.results)}")
        self.logger.info(f"Passed: {self.passed}")
        self.logger.info(f"Failed: {self.failed}")
        self.logger.info(f"Success Rate: {(self.passed/len(self.results)*100):.1f}%")
        self.logger.info(f"Total Time: {total_time:.2f} seconds")
        self.logger.info(f"Average Response Time: {sum(r['response_time'] for r in self.results)/len(self.results):.2f}s")
        
        # Detailed results
        self.logger.info(f"\n{'='*80}")
        self.logger.info("DETAILED RESULTS")
        self.logger.info(f"{'='*80}")
        
        for result in self.results:
            status = "✅ PASS" if result['passed'] else "❌ FAIL"
            self.logger.info(f"{status} | {result['name']} | {result['response_time']:.2f}s")
            if not result['passed'] and result['error_details']:
                self.logger.info(f"      Error: {result['error_details']}")
        
        # Save report to file
        report_data = {
            'summary': {
                'total_tests': len(self.results),
                'passed': self.passed,
                'failed': self.failed,
                'success_rate': self.passed/len(self.results)*100,
                'total_time': total_time,
                'average_response_time': sum(r['response_time'] for r in self.results)/len(self.results)
            },
            'results': self.results
        }
        
        with open('edge_case_test_report.json', 'w') as f:
            json.dump(report_data, f, indent=2)
        
        self.logger.info(f"\nDetailed report saved to: edge_case_test_report.json")
        
        # System recommendations
        self.logger.info(f"\n{'='*80}")
        self.logger.info("SYSTEM HEALTH ASSESSMENT")
        self.logger.info(f"{'='*80}")
        
        if self.passed / len(self.results) >= 0.8:
            self.logger.info("🟢 EXCELLENT: System handles edge cases very well")
        elif self.passed / len(self.results) >= 0.6:
            self.logger.info("🟡 GOOD: System handles most edge cases adequately")
        else:
            self.logger.info("🔴 POOR: System needs improvement in error handling")
        
        # Performance assessment
        avg_response_time = sum(r['response_time'] for r in self.results) / len(self.results)
        if avg_response_time < 5:
            self.logger.info("🟢 EXCELLENT: Response times are very good")
        elif avg_response_time < 15:
            self.logger.info("🟡 ACCEPTABLE: Response times are reasonable")
        else:
            self.logger.info("🔴 SLOW: Response times need optimization")

async def main():
    """Main test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run edge case tests for Shopify Insights Fetcher')
    parser.add_argument('--url', default='http://localhost:5000', help='Base URL for testing')
    parser.add_argument('--quick', action='store_true', help='Run only critical tests')
    
    args = parser.parse_args()
    
    tester = EdgeCaseTester(args.url)
    
    if args.quick:
        # Run only critical tests
        global TEST_CASES
        TEST_CASES = [tc for tc in TEST_CASES if tc['name'] in [
            'Invalid URL - Malformed',
            'Invalid URL - Non-existent domain', 
            'Valid Shopify Store'
        ]]
    
    await tester.run_all_tests()
    
    # Exit with appropriate code
    if tester.failed == 0:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())