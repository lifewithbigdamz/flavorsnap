"""
Zero-Knowledge Proof Handlers for Privacy-Preserving Computations
Handles ZK proof generation, verification, and circuit management
"""

import asyncio
import logging
import json
import time
import hashlib
import os
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import aiohttp
from web3 import Web3
from web3.contract import Contract

logger = logging.getLogger(__name__)

class CircuitType(Enum):
    AGE_VERIFICATION = "age_verification"
    IDENTITY_VERIFICATION = "identity_verification"
    FINANCIAL_VERIFICATION = "financial_verification"
    MEMBERSHIP_VERIFICATION = "membership_verification"
    QUALIFICATION_VERIFICATION = "qualification_verification"

class ProofStatus(Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    EXPIRED = "expired"

@dataclass
class ZKCircuit:
    """Data structure for ZK circuits"""
    name: str
    description: str
    creator: str
    circuit_type: CircuitType
    is_active: bool
    created_time: float
    verification_count: int
    circuit_file: str
    verification_key: Dict[str, Any]
    proving_key: Dict[str, Any]

@dataclass
class ZKProof:
    """Data structure for ZK proofs"""
    proof_id: str
    circuit_name: str
    creator: str
    public_inputs: List[str]
    proof_data: Dict[str, Any]
    status: ProofStatus
    created_time: float
    verified_time: Optional[float]
    verification_result: Optional[bool]
    gas_used: int

@dataclass
class VerificationRequest:
    """Data structure for verification requests"""
    request_id: str
    circuit_name: str
    proof_data: Dict[str, Any]
    public_inputs: List[str]
    requester: str
    created_time: float
    status: ProofStatus
    result: Optional[bool]

class ZKProofHandler:
    """Zero-Knowledge Proof Handler for privacy-preserving computations"""
    
    def __init__(self, web3_provider: str, contract_address: str, contract_abi: Dict):
        self.web3 = Web3(Web3.HTTPProvider(web3_provider))
        self.contract = self.web3.eth.contract(
            address=contract_address,
            abi=contract_abi
        )
        self.circuits: Dict[str, ZKCircuit] = {}
        self.proofs: Dict[str, ZKProof] = {}
        self.verification_requests: Dict[str, VerificationRequest] = {}
        self.circuit_cache = {}
        
        # Initialize built-in circuits
        self._initialize_builtin_circuits()
    
    def _initialize_builtin_circuits(self):
        """Initialize built-in ZK circuits"""
        builtin_circuits = [
            {
                "name": "age_verification",
                "description": "Verify age without revealing actual age",
                "type": CircuitType.AGE_VERIFICATION,
                "public_inputs": ["age_commitment", "timestamp"],
                "private_inputs": ["actual_age"]
            },
            {
                "name": "identity_verification",
                "description": "Verify identity without revealing personal data",
                "type": CircuitType.IDENTITY_VERIFICATION,
                "public_inputs": ["identity_commitment", "nonce"],
                "private_inputs": ["identity_data"]
            },
            {
                "name": "financial_verification",
                "description": "Verify financial status without revealing amounts",
                "type": CircuitType.FINANCIAL_VERIFICATION,
                "public_inputs": ["financial_commitment", "threshold"],
                "private_inputs": ["actual_amount"]
            },
            {
                "name": "membership_verification",
                "description": "Verify membership without revealing identity",
                "type": CircuitType.MEMBERSHIP_VERIFICATION,
                "public_inputs": ["membership_commitment", "group_id"],
                "private_inputs": ["member_id"]
            },
            {
                "name": "qualification_verification",
                "description": "Verify qualifications without revealing details",
                "type": CircuitType.QUALIFICATION_VERIFICATION,
                "public_inputs": ["qualification_commitment", "level"],
                "private_inputs": ["qualification_details"]
            }
        ]
        
        for circuit_data in builtin_circuits:
            circuit = ZKCircuit(
                name=circuit_data["name"],
                description=circuit_data["description"],
                creator="system",
                circuit_type=circuit_data["type"],
                is_active=True,
                created_time=time.time(),
                verification_count=0,
                circuit_file=f"{circuit_data['name']}.circom",
                verification_key={},
                proving_key={}
            )
            self.circuits[circuit.name] = circuit
    
    async def generate_proof(
        self,
        circuit_name: str,
        private_inputs: Dict[str, Any],
        public_inputs: List[str],
        private_key: str
    ) -> Optional[ZKProof]:
        """Generate a ZK proof for the given circuit"""
        try:
            if circuit_name not in self.circuits:
                logger.error(f"Circuit {circuit_name} not found")
                return None
            
            circuit = self.circuits[circuit_name]
            if not circuit.is_active:
                logger.error(f"Circuit {circuit_name} is not active")
                return None
            
            # Generate witness (simplified - in production would use actual circuit compilation)
            witness = await self._generate_witness(circuit_name, private_inputs, public_inputs)
            if not witness:
                logger.error("Failed to generate witness")
                return None
            
            # Generate proof (simplified - in production would use actual proving algorithm)
            proof_data = await self._generate_proof_data(circuit_name, witness)
            if not proof_data:
                logger.error("Failed to generate proof")
                return None
            
            # Create proof record
            proof_id = hashlib.sha256(
                f"{circuit_name}:{time.time()}:{private_inputs}".encode()
            ).hexdigest()
            
            proof = ZKProof(
                proof_id=proof_id,
                circuit_name=circuit_name,
                creator=self.web3.eth.account.from_key(private_key).address,
                public_inputs=public_inputs,
                proof_data=proof_data,
                status=ProofStatus.PENDING,
                created_time=time.time(),
                verified_time=None,
                verification_result=None,
                gas_used=0
            )
            
            self.proofs[proof_id] = proof
            logger.info(f"Generated proof {proof_id} for circuit {circuit_name}")
            return proof
            
        except Exception as e:
            logger.error(f"Error generating proof: {str(e)}")
            return None
    
    async def verify_proof(
        self,
        circuit_name: str,
        proof_data: Dict[str, Any],
        public_inputs: List[str],
        private_key: str
    ) -> Optional[bool]:
        """Verify a ZK proof on-chain"""
        try:
            account = self.web3.eth.account.from_key(private_key)
            
            # Get verification fee
            verification_fee = self.contract.functions.verificationFee().call()
            
            # Build transaction
            tx = self.contract.functions.verifyProof(
                circuit_name,
                self._convert_proof_format(proof_data),
                [int(inp) for inp in public_inputs]
            ).build_transaction({
                'from': account.address,
                'value': verification_fee,
                'gas': 500000,
                'gasPrice': self.web3.eth.gas_price,
                'nonce': self.web3.eth.get_transaction_count(account.address)
            })
            
            # Sign and send transaction
            signed_tx = self.web3.eth.account.sign_transaction(tx, private_key)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            # Wait for confirmation
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status == 1:
                # Get verification result from events
                logs = self.contract.events.ProofVerified().process_receipt(receipt)
                if logs:
                    is_valid = logs[0]['args']['isValid']
                    logger.info(f"Proof verification result: {is_valid}")
                    return is_valid
                else:
                    logger.error("Could not extract verification result from logs")
                    return None
            else:
                logger.error("Proof verification transaction failed")
                return None
                
        except Exception as e:
            logger.error(f"Error verifying proof: {str(e)}")
            return None
    
    async def batch_verify_proofs(
        self,
        circuit_name: str,
        proofs_data: List[Dict[str, Any]],
        public_inputs_array: List[List[str]],
        private_key: str
    ) -> Optional[List[bool]]:
        """Batch verify multiple ZK proofs"""
        try:
            account = self.web3.eth.account.from_key(private_key)
            
            # Get verification fee
            verification_fee = self.contract.functions.verificationFee().call()
            total_fee = verification_fee * len(proofs_data)
            
            # Convert proofs to contract format
            contract_proofs = [self._convert_proof_format(proof) for proof in proofs_data]
            contract_inputs = [[int(inp) for inp in inputs] for inputs in public_inputs_array]
            
            # Build transaction
            tx = self.contract.functions.batchVerifyProofs(
                circuit_name,
                contract_proofs,
                contract_inputs
            ).build_transaction({
                'from': account.address,
                'value': total_fee,
                'gas': 500000 * len(proofs_data),
                'gasPrice': self.web3.eth.gas_price,
                'nonce': self.web3.eth.get_transaction_count(account.address)
            })
            
            # Sign and send transaction
            signed_tx = self.web3.eth.account.sign_transaction(tx, private_key)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            # Wait for confirmation
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status == 1:
                # Get batch verification results from events
                results = []
                logs = self.contract.events.ProofVerified().process_receipt(receipt)
                for log in logs:
                    results.append(log['args']['isValid'])
                
                logger.info(f"Batch verification completed: {len(results)} proofs")
                return results
            else:
                logger.error("Batch verification transaction failed")
                return None
                
        except Exception as e:
            logger.error(f"Error in batch verification: {str(e)}")
            return None
    
    async def register_circuit(
        self,
        name: str,
        description: str,
        circuit_file: str,
        verification_key: Dict[str, Any],
        private_key: str
    ) -> bool:
        """Register a new ZK circuit"""
        try:
            account = self.web3.eth.account.from_key(private_key)
            
            # Build verification key for contract
            vk = self._convert_verification_key(verification_key)
            
            # Build transaction
            tx = self.contract.functions.registerCircuit(
                name,
                description,
                vk
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
                # Store circuit locally
                circuit = ZKCircuit(
                    name=name,
                    description=description,
                    creator=account.address,
                    circuit_type=CircuitType.IDENTITY_VERIFICATION,  # Default type
                    is_active=True,
                    created_time=time.time(),
                    verification_count=0,
                    circuit_file=circuit_file,
                    verification_key=verification_key,
                    proving_key={}
                )
                self.circuits[name] = circuit
                
                logger.info(f"Circuit {name} registered successfully")
                return True
            else:
                logger.error("Circuit registration failed")
                return False
                
        except Exception as e:
            logger.error(f"Error registering circuit: {str(e)}")
            return False
    
    async def _generate_witness(
        self,
        circuit_name: str,
        private_inputs: Dict[str, Any],
        public_inputs: List[str]
    ) -> Optional[List[str]]:
        """Generate witness for ZK proof (simplified)"""
        try:
            # In production, this would compile the circuit and generate actual witness
            # For now, we'll create a mock witness
            witness = []
            
            # Add public inputs
            witness.extend(public_inputs)
            
            # Add private inputs (hashed for privacy)
            for key, value in private_inputs.items():
                witness.append(hashlib.sha256(str(value).encode()).hexdigest())
            
            return witness
            
        except Exception as e:
            logger.error(f"Error generating witness: {str(e)}")
            return None
    
    async def _generate_proof_data(
        self,
        circuit_name: str,
        witness: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Generate proof data (simplified)"""
        try:
            # In production, this would use actual proving algorithm
            # For now, we'll create mock proof data
            proof_data = {
                "a": [hash(witness[0]) % 2**256, hash(witness[1]) % 2**256],
                "b": [
                    [hash(witness[2]) % 2**256, hash(witness[3]) % 2**256],
                    [hash(witness[4]) % 2**256, hash(witness[5]) % 2**256]
                ],
                "c": [hash(witness[6]) % 2**256, hash(witness[7]) % 2**256]
            }
            
            return proof_data
            
        except Exception as e:
            logger.error(f"Error generating proof data: {str(e)}")
            return None
    
    def _convert_proof_format(self, proof_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert proof data to contract format"""
        return {
            "a": proof_data.get("a", [0, 0]),
            "b": proof_data.get("b", [[0, 0], [0, 0]]),
            "c": proof_data.get("c", [0, 0])
        }
    
    def _convert_verification_key(self, vk: Dict[str, Any]) -> Dict[str, Any]:
        """Convert verification key to contract format"""
        return {
            "alpha": vk.get("alpha", [0, 0]),
            "beta": vk.get("beta", [[0, 0], [0, 0]]),
            "gamma": vk.get("gamma", [0, 0]),
            "delta": vk.get("delta", [0, 0]),
            "gamma_abc": vk.get("gamma_abc", [0, 0])
        }
    
    async def get_circuit_info(self, circuit_name: str) -> Optional[Dict[str, Any]]:
        """Get circuit information"""
        try:
            if circuit_name in self.circuits:
                circuit = self.circuits[circuit_name]
                return {
                    "name": circuit.name,
                    "description": circuit.description,
                    "creator": circuit.creator,
                    "circuit_type": circuit.circuit_type.value,
                    "is_active": circuit.is_active,
                    "created_time": circuit.created_time,
                    "verification_count": circuit.verification_count
                }
            else:
                # Try to get from contract
                circuit_info = self.contract.functions.getCircuitInfo(circuit_name).call()
                return {
                    "name": circuit_info[0],
                    "description": circuit_info[1],
                    "creator": circuit_info[2],
                    "is_active": circuit_info[3],
                    "created_time": circuit_info[4],
                    "verification_count": circuit_info[5]
                }
                
        except Exception as e:
            logger.error(f"Error getting circuit info: {str(e)}")
            return None
    
    async def get_user_verifications(self, user_address: str) -> List[Dict[str, Any]]:
        """Get user verification history"""
        try:
            verifications = self.contract.functions.getUserVerifications(user_address).call()
            
            result = []
            for verification in verifications:
                result.append({
                    "proof_hash": verification[0],
                    "verifier": verification[1],
                    "timestamp": verification[2],
                    "is_valid": verification[3],
                    "circuit_name": verification[4],
                    "gas_used": verification[5]
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting user verifications: {str(e)}")
            return []
    
    async def get_verification_stats(self) -> Dict[str, Any]:
        """Get verification statistics"""
        try:
            stats = self.contract.functions.getVerificationStats().call()
            
            return {
                "total_verifications": stats[0],
                "active_circuits": stats[1],
                "total_fees": stats[2]
            }
            
        except Exception as e:
            logger.error(f"Error getting verification stats: {str(e)}")
            return {}
    
    async def is_proof_used(self, circuit_name: str, proof_hash: str) -> bool:
        """Check if a proof has been used"""
        try:
            return self.contract.functions.isProofUsed(circuit_name, proof_hash).call()
            
        except Exception as e:
            logger.error(f"Error checking proof usage: {str(e)}")
            return False
    
    async def verify_age_proof(
        self,
        age: int,
        min_age: int,
        private_key: str
    ) -> Optional[bool]:
        """Generate and verify age proof"""
        try:
            # Generate age commitment
            age_commitment = hashlib.sha256(f"{age}:{time.time()}".encode()).hexdigest()
            
            # Generate proof
            proof = await self.generate_proof(
                "age_verification",
                {"actual_age": age},
                [age_commitment, str(min_age)],
                private_key
            )
            
            if not proof:
                return None
            
            # Verify proof
            return await self.verify_proof(
                "age_verification",
                proof.proof_data,
                proof.public_inputs,
                private_key
            )
            
        except Exception as e:
            logger.error(f"Error in age verification: {str(e)}")
            return None
    
    async def verify_identity_proof(
        self,
        identity_data: str,
        nonce: str,
        private_key: str
    ) -> Optional[bool]:
        """Generate and verify identity proof"""
        try:
            # Generate identity commitment
            identity_commitment = hashlib.sha256(f"{identity_data}:{nonce}".encode()).hexdigest()
            
            # Generate proof
            proof = await self.generate_proof(
                "identity_verification",
                {"identity_data": identity_data},
                [identity_commitment, nonce],
                private_key
            )
            
            if not proof:
                return None
            
            # Verify proof
            return await self.verify_proof(
                "identity_verification",
                proof.proof_data,
                proof.public_inputs,
                private_key
            )
            
        except Exception as e:
            logger.error(f"Error in identity verification: {str(e)}")
            return None
    
    async def verify_financial_proof(
        self,
        actual_amount: float,
        threshold: float,
        private_key: str
    ) -> Optional[bool]:
        """Generate and verify financial proof"""
        try:
            # Generate financial commitment
            financial_commitment = hashlib.sha256(f"{actual_amount}:{time.time()}".encode()).hexdigest()
            
            # Generate proof
            proof = await self.generate_proof(
                "financial_verification",
                {"actual_amount": actual_amount},
                [financial_commitment, str(threshold)],
                private_key
            )
            
            if not proof:
                return None
            
            # Verify proof
            return await self.verify_proof(
                "financial_verification",
                proof.proof_data,
                proof.public_inputs,
                private_key
            )
            
        except Exception as e:
            logger.error(f"Error in financial verification: {str(e)}")
            return None
    
    def get_circuit_names(self) -> List[str]:
        """Get all circuit names"""
        return list(self.circuits.keys())
    
    def get_proof_by_id(self, proof_id: str) -> Optional[ZKProof]:
        """Get proof by ID"""
        return self.proofs.get(proof_id)
    
    async def update_circuit_status(self, circuit_name: str, is_active: bool, private_key: str) -> bool:
        """Update circuit status"""
        try:
            account = self.web3.eth.account.from_key(private_key)
            
            # Build transaction
            tx = self.contract.functions.updateCircuitStatus(
                circuit_name,
                is_active
            ).build_transaction({
                'from': account.address,
                'gas': 100000,
                'gasPrice': self.web3.eth.gas_price,
                'nonce': self.web3.eth.get_transaction_count(account.address)
            })
            
            # Sign and send transaction
            signed_tx = self.web3.eth.account.sign_transaction(tx, private_key)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            # Wait for confirmation
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status == 1:
                # Update local circuit
                if circuit_name in self.circuits:
                    self.circuits[circuit_name].is_active = is_active
                
                logger.info(f"Circuit {circuit_name} status updated to {is_active}")
                return True
            else:
                logger.error("Circuit status update failed")
                return False
                
        except Exception as e:
            logger.error(f"Error updating circuit status: {str(e)}")
            return False
