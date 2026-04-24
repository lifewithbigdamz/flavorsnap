"""
Advanced Oracle Handlers for Real-World Data Integration
Handles oracle requests, data validation, and reputation management
"""

import asyncio
import logging
import hashlib
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import aiohttp
import requests
from web3 import Web3
from web3.contract import Contract

logger = logging.getLogger(__name__)

class OracleStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"

class ValidationLevel(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class OracleData:
    """Data structure for oracle information"""
    provider_address: str
    name: str
    reputation: int
    fee: float
    status: OracleStatus
    supported_data_types: List[str]
    total_requests: int
    successful_requests: int
    last_update: float
    data_points: Dict[str, Any]

@dataclass
class DataRequest:
    """Data structure for data requests"""
    request_id: int
    requester: str
    data_type: str
    deadline: float
    bounty: float
    min_reputation: int
    fulfilled: bool
    response_time: Optional[float]
    data_hash: Optional[str]
    selected_oracle: Optional[str]

@dataclass
class ValidationReport:
    """Data structure for validation reports"""
    request_id: int
    validator: str
    is_valid: bool
    reason: str
    timestamp: float
    confidence_score: float

class AdvancedOracleHandler:
    """Advanced Oracle Handler for data integration and validation"""
    
    def __init__(self, web3_provider: str, contract_address: str, contract_abi: Dict):
        self.web3 = Web3(Web3.HTTPProvider(web3_provider))
        self.contract = self.web3.eth.contract(
            address=contract_address,
            abi=contract_abi
        )
        self.oracles: Dict[str, OracleData] = {}
        self.data_requests: Dict[int, DataRequest] = {}
        self.validation_reports: Dict[int, List[ValidationReport]] = {}
        self.external_apis = {}
        self.validation_cache = {}
        
    async def register_oracle(
        self,
        name: str,
        fee: float,
        supported_data_types: List[str],
        private_key: str
    ) -> bool:
        """Register a new oracle provider"""
        try:
            account = self.web3.eth.account.from_key(private_key)
            
            # Build transaction
            tx = self.contract.functions.registerOracle(
                name,
                int(fee * 1e18),  # Convert to wei
                supported_data_types
            ).build_transaction({
                'from': account.address,
                'gas': 300000,
                'gasPrice': self.web3.eth.gas_price,
                'nonce': self.web3.eth.get_transaction_count(account.address)
            })
            
            # Sign and send transaction
            signed_tx = self.web3.eth.account.sign_transaction(tx, private_key)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            # Wait for confirmation
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status == 1:
                # Store oracle data locally
                self.oracles[account.address] = OracleData(
                    provider_address=account.address,
                    name=name,
                    reputation=100,
                    fee=fee,
                    status=OracleStatus.ACTIVE,
                    supported_data_types=supported_data_types,
                    total_requests=0,
                    successful_requests=0,
                    last_update=time.time(),
                    data_points={}
                )
                logger.info(f"Oracle {name} registered successfully")
                return True
            else:
                logger.error("Oracle registration failed")
                return False
                
        except Exception as e:
            logger.error(f"Error registering oracle: {str(e)}")
            return False
    
    async def request_data(
        self,
        data_type: str,
        deadline: float,
        bounty: float,
        min_reputation: int,
        private_key: str
    ) -> Optional[int]:
        """Request data from oracles"""
        try:
            account = self.web3.eth.account.from_key(private_key)
            
            # Build transaction
            tx = self.contract.functions.requestData(
                data_type,
                int(deadline),
                int(bounty * 1e18),  # Convert to wei
                min_reputation
            ).build_transaction({
                'from': account.address,
                'value': int(bounty * 1e18),  # Send bounty with transaction
                'gas': 300000,
                'gasPrice': self.web3.eth.gas_price,
                'nonce': self.web3.eth.get_transaction_count(account.address)
            })
            
            # Sign and send transaction
            signed_tx = self.web3.eth.account.sign_transaction(tx, private_key)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            # Wait for confirmation
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status == 1:
                # Get request ID from events
                logs = self.contract.events.DataRequested().process_receipt(receipt)
                if logs:
                    request_id = logs[0]['args']['requestId']
                    logger.info(f"Data request {request_id} submitted successfully")
                    return request_id
                else:
                    logger.error("Could not extract request ID from logs")
                    return None
            else:
                logger.error("Data request failed")
                return None
                
        except Exception as e:
            logger.error(f"Error requesting data: {str(e)}")
            return None
    
    async def provide_data(
        self,
        request_id: int,
        data_value: Any,
        private_key: str
    ) -> bool:
        """Provide data for a request"""
        try:
            account = self.web3.eth.account.from_key(private_key)
            
            # Get request details
            request = await self.get_request_details(request_id)
            if not request:
                logger.error(f"Request {request_id} not found")
                return False
            
            # Validate data
            validation_result = await self.validate_data(request.data_type, data_value)
            if not validation_result['is_valid']:
                logger.error(f"Data validation failed: {validation_result['reason']}")
                return False
            
            # Create data hash
            data_hash = hashlib.sha256(str(data_value).encode()).hexdigest()
            
            # Build transaction
            tx = self.contract.functions.provideData(
                request_id,
                data_hash,
                int(data_value) if isinstance(data_value, (int, float)) else 0
            ).build_transaction({
                'from': account.address,
                'gas': 300000,
                'gasPrice': self.web3.eth.gas_price,
                'nonce': self.web3.eth.get_transaction_count(account.address)
            })
            
            # Sign and send transaction
            signed_tx = self.web3.eth.account.sign_transaction(tx, private_key)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            # Wait for confirmation
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status == 1:
                # Update local oracle data
                if account.address in self.oracles:
                    oracle = self.oracles[account.address]
                    oracle.total_requests += 1
                    oracle.successful_requests += 1
                    oracle.last_update = time.time()
                    oracle.data_points[request.data_type] = data_value
                
                logger.info(f"Data provided for request {request_id}")
                return True
            else:
                logger.error("Data provision failed")
                return False
                
        except Exception as e:
            logger.error(f"Error providing data: {str(e)}")
            return False
    
    async def validate_data(
        self,
        data_type: str,
        data_value: Any
    ) -> Dict[str, Any]:
        """Validate data based on type and external sources"""
        try:
            # Check cache first
            cache_key = f"{data_type}:{hash(str(data_value))}"
            if cache_key in self.validation_cache:
                return self.validation_cache[cache_key]
            
            validation_result = {
                'is_valid': False,
                'reason': '',
                'confidence_score': 0.0,
                'external_sources': []
            }
            
            # Type-specific validation
            if data_type == "price":
                validation_result = await self._validate_price_data(data_value)
            elif data_type == "weather":
                validation_result = await self._validate_weather_data(data_value)
            elif data_type == "food_quality":
                validation_result = await self._validate_food_quality_data(data_value)
            elif data_type == "market_data":
                validation_result = await self._validate_market_data(data_value)
            else:
                validation_result = await self._validate_generic_data(data_value)
            
            # Cache result
            self.validation_cache[cache_key] = validation_result
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating data: {str(e)}")
            return {
                'is_valid': False,
                'reason': f'Validation error: {str(e)}',
                'confidence_score': 0.0,
                'external_sources': []
            }
    
    async def _validate_price_data(self, price_value: Any) -> Dict[str, Any]:
        """Validate price data against external sources"""
        try:
            price = float(price_value)
            
            # Fetch current price from external APIs
            external_prices = []
            async with aiohttp.ClientSession() as session:
                # Example: Fetch from multiple price APIs
                apis = [
                    'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd',
                    'https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT'
                ]
                
                for api_url in apis:
                    try:
                        async with session.get(api_url) as response:
                            if response.status == 200:
                                data = await response.json()
                                if 'bitcoin' in data:
                                    external_prices.append(data['bitcoin']['usd'])
                                elif 'price' in data:
                                    external_prices.append(float(data['price']))
                    except Exception as e:
                        logger.warning(f"Failed to fetch from {api_url}: {str(e)}")
            
            # Calculate deviation
            if external_prices:
                avg_external_price = sum(external_prices) / len(external_prices)
                deviation = abs(price - avg_external_price) / avg_external_price
                
                is_valid = deviation < 0.05  # 5% tolerance
                confidence_score = max(0, 1 - deviation * 10)  # Linear confidence decay
                
                return {
                    'is_valid': is_valid,
                    'reason': f'Price deviation: {deviation:.2%}',
                    'confidence_score': confidence_score,
                    'external_sources': external_prices
                }
            else:
                return {
                    'is_valid': True,  # No external data to compare
                    'reason': 'No external data available for validation',
                    'confidence_score': 0.5,
                    'external_sources': []
                }
                
        except Exception as e:
            logger.error(f"Error validating price data: {str(e)}")
            return {
                'is_valid': False,
                'reason': f'Price validation error: {str(e)}',
                'confidence_score': 0.0,
                'external_sources': []
            }
    
    async def _validate_weather_data(self, weather_value: Any) -> Dict[str, Any]:
        """Validate weather data"""
        try:
            # Weather validation logic
            if isinstance(weather_value, dict):
                temp = weather_value.get('temperature', 0)
                humidity = weather_value.get('humidity', 0)
                
                # Basic sanity checks
                if -100 <= temp <= 60 and 0 <= humidity <= 100:
                    return {
                        'is_valid': True,
                        'reason': 'Weather data within reasonable ranges',
                        'confidence_score': 0.8,
                        'external_sources': []
                    }
                else:
                    return {
                        'is_valid': False,
                        'reason': 'Weather data outside reasonable ranges',
                        'confidence_score': 0.2,
                        'external_sources': []
                    }
            else:
                return {
                    'is_valid': False,
                    'reason': 'Weather data must be a dictionary',
                    'confidence_score': 0.0,
                    'external_sources': []
                }
                
        except Exception as e:
            logger.error(f"Error validating weather data: {str(e)}")
            return {
                'is_valid': False,
                'reason': f'Weather validation error: {str(e)}',
                'confidence_score': 0.0,
                'external_sources': []
            }
    
    async def _validate_food_quality_data(self, quality_value: Any) -> Dict[str, Any]:
        """Validate food quality data"""
        try:
            if isinstance(quality_value, (int, float)):
                quality_score = float(quality_value)
                if 0 <= quality_score <= 100:
                    return {
                        'is_valid': True,
                        'reason': 'Food quality score within valid range',
                        'confidence_score': 0.9,
                        'external_sources': []
                    }
                else:
                    return {
                        'is_valid': False,
                        'reason': 'Food quality score must be between 0 and 100',
                        'confidence_score': 0.0,
                        'external_sources': []
                    }
            else:
                return {
                    'is_valid': False,
                    'reason': 'Food quality must be a numeric value',
                    'confidence_score': 0.0,
                    'external_sources': []
                }
                
        except Exception as e:
            logger.error(f"Error validating food quality data: {str(e)}")
            return {
                'is_valid': False,
                'reason': f'Food quality validation error: {str(e)}',
                'confidence_score': 0.0,
                'external_sources': []
            }
    
    async def _validate_market_data(self, market_value: Any) -> Dict[str, Any]:
        """Validate market data"""
        try:
            # Market data validation logic
            if isinstance(market_value, dict):
                required_fields = ['volume', 'price', 'timestamp']
                if all(field in market_value for field in required_fields):
                    return {
                        'is_valid': True,
                        'reason': 'Market data contains required fields',
                        'confidence_score': 0.85,
                        'external_sources': []
                    }
                else:
                    return {
                        'is_valid': False,
                        'reason': 'Market data missing required fields',
                        'confidence_score': 0.0,
                        'external_sources': []
                    }
            else:
                return {
                    'is_valid': False,
                    'reason': 'Market data must be a dictionary',
                    'confidence_score': 0.0,
                    'external_sources': []
                }
                
        except Exception as e:
            logger.error(f"Error validating market data: {str(e)}")
            return {
                'is_valid': False,
                'reason': f'Market data validation error: {str(e)}',
                'confidence_score': 0.0,
                'external_sources': []
            }
    
    async def _validate_generic_data(self, data_value: Any) -> Dict[str, Any]:
        """Generic data validation"""
        try:
            # Basic validation - ensure data is not None and is serializable
            if data_value is not None:
                json.dumps(data_value)  # Test serializability
                return {
                    'is_valid': True,
                    'reason': 'Data is valid and serializable',
                    'confidence_score': 0.6,
                    'external_sources': []
                }
            else:
                return {
                    'is_valid': False,
                    'reason': 'Data cannot be None',
                    'confidence_score': 0.0,
                    'external_sources': []
                }
                
        except Exception as e:
            logger.error(f"Error validating generic data: {str(e)}")
            return {
                'is_valid': False,
                'reason': f'Generic validation error: {str(e)}',
                'confidence_score': 0.0,
                'external_sources': []
            }
    
    async def get_request_details(self, request_id: int) -> Optional[DataRequest]:
        """Get details of a data request"""
        try:
            request_data = self.contract.functions.dataRequests(request_id).call()
            
            request = DataRequest(
                request_id=request_data[0],
                requester=request_data[1],
                data_type=request_data[2],
                deadline=float(request_data[3]),
                bounty=float(request_data[4]) / 1e18,  # Convert from wei
                min_reputation=request_data[5],
                fulfilled=request_data[6],
                response_time=float(request_data[7]) if request_data[7] > 0 else None,
                data_hash=request_data[8].hex() if request_data[8] else None,
                selected_oracle=request_data[9] if request_data[9] != '0x0000000000000000000000000000000000000000' else None
            )
            
            return request
            
        except Exception as e:
            logger.error(f"Error getting request details: {str(e)}")
            return None
    
    async def get_oracle_stats(self, oracle_address: str) -> Optional[Dict[str, Any]]:
        """Get oracle statistics"""
        try:
            stats = self.contract.functions.getOracleStats(oracle_address).call()
            
            return {
                'reputation': stats[0],
                'total_requests': stats[1],
                'successful_requests': stats[2],
                'fee': float(stats[3]) / 1e18,
                'is_active': stats[4]
            }
            
        except Exception as e:
            logger.error(f"Error getting oracle stats: {str(e)}")
            return None
    
    async def submit_validation(
        self,
        request_id: int,
        is_valid: bool,
        reason: str,
        private_key: str
    ) -> bool:
        """Submit validation report"""
        try:
            account = self.web3.eth.account.from_key(private_key)
            
            # Build transaction
            tx = self.contract.functions.submitValidation(
                request_id,
                is_valid,
                reason
            ).build_transaction({
                'from': account.address,
                'gas': 200000,
                'gasPrice': self.web3.eth.gas_price,
                'nonce': self.web3.eth.get_transaction_count(account.address)
            })
            
            # Sign and send transaction
            signed_tx = self.web3.eth.account.sign_transaction(tx, private_key)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            # Wait for confirmation
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status == 1:
                logger.info(f"Validation submitted for request {request_id}")
                return True
            else:
                logger.error("Validation submission failed")
                return False
                
        except Exception as e:
            logger.error(f"Error submitting validation: {str(e)}")
            return False
    
    async def get_available_oracles(self, data_type: str) -> List[str]:
        """Get available oracles for a specific data type"""
        try:
            oracles = self.contract.functions.getAvailableOracles(data_type).call()
            return oracles
            
        except Exception as e:
            logger.error(f"Error getting available oracles: {str(e)}")
            return []
    
    def get_oracle_success_rate(self, oracle_address: str) -> float:
        """Calculate oracle success rate"""
        try:
            success_rate = self.contract.functions.getOracleSuccessRate(oracle_address).call()
            return float(success_rate)
            
        except Exception as e:
            logger.error(f"Error getting oracle success rate: {str(e)}")
            return 0.0
    
    async def monitor_oracle_performance(self) -> Dict[str, Any]:
        """Monitor oracle performance metrics"""
        try:
            performance_metrics = {
                'total_oracles': len(self.oracles),
                'active_oracles': sum(1 for o in self.oracles.values() if o.status == OracleStatus.ACTIVE),
                'average_reputation': 0,
                'total_requests': sum(o.total_requests for o in self.oracles.values()),
                'successful_requests': sum(o.successful_requests for o in self.oracles.values()),
                'average_response_time': 0,
                'data_types_coverage': {}
            }
            
            if self.oracles:
                performance_metrics['average_reputation'] = sum(o.reputation for o in self.oracles.values()) / len(self.oracles)
            
            # Calculate data type coverage
            for oracle in self.oracles.values():
                for data_type in oracle.supported_data_types:
                    if data_type not in performance_metrics['data_types_coverage']:
                        performance_metrics['data_types_coverage'][data_type] = 0
                    performance_metrics['data_types_coverage'][data_type] += 1
            
            return performance_metrics
            
        except Exception as e:
            logger.error(f"Error monitoring oracle performance: {str(e)}")
            return {}
