// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/utils/math/SafeMath.sol";

/**
 * @title ZKProofVerifier
 * @dev Zero-Knowledge Proof verification system for privacy-preserving computations
 * @notice This contract provides ZK proof verification and management capabilities
 */
contract ZKProofVerifier is Ownable, ReentrancyGuard, Pausable {
    using SafeMath for uint256;

    // ZK-SNARK verification keys (simplified representation)
    struct VerificationKey {
        uint256[2] alpha;
        uint256[2][2] beta;
        uint256[2] gamma;
        uint256[2] delta;
        uint256[2] gamma_abc;
    }

    // Proof structure
    struct ZKProof {
        uint256[2] a;
        uint256[2][2] b;
        uint256[2] c;
    }

    // Circuit registry
    struct ZKCircuit {
        string name;
        string description;
        address creator;
        VerificationKey vk;
        bool isActive;
        uint256 createdTime;
        uint256 verificationCount;
        mapping(bytes32 => bool) usedProofs; // proofHash => used
    }

    // Verification record
    struct VerificationRecord {
        bytes32 proofHash;
        address verifier;
        uint256 timestamp;
        bool isValid;
        string circuitName;
        uint256 gasUsed;
    }

    mapping(string => ZKCircuit) public circuits;
    mapping(address => VerificationRecord[]) public userVerifications;
    mapping(bytes32 => VerificationRecord) public proofRecords;
    
    string[] public circuitNames;
    uint256 public verificationFee = 0.001 ether;
    uint256 public maxVerificationGas = 500000;

    // Events
    event CircuitRegistered(string indexed name, address indexed creator);
    event ProofVerified(bytes32 indexed proofHash, address indexed verifier, bool isValid);
    event CircuitUpdated(string indexed name, bool isActive);
    event VerificationFeeUpdated(uint256 newFee);

    // Modifiers
    modifier circuitExists(string memory circuitName) {
        require(bytes(circuits[circuitName].name).length > 0, "Circuit does not exist");
        _;
    }

    modifier circuitActive(string memory circuitName) {
        require(circuits[circuitName].isActive, "Circuit is not active");
        _;
    }

    modifier validProof(ZKProof memory proof) {
        require(proof.a.length == 2, "Invalid proof A");
        require(proof.b.length == 2, "Invalid proof B");
        require(proof.c.length == 2, "Invalid proof C");
        _;
    }

    /**
     * @dev Register a new ZK circuit
     * @param name Circuit name
     * @param description Circuit description
     * @param vk Verification key
     */
    function registerCircuit(
        string memory name,
        string memory description,
        VerificationKey memory vk
    ) external onlyOwner {
        require(bytes(name).length > 0, "Name cannot be empty");
        require(bytes(circuits[name].name).length == 0, "Circuit already exists");

        ZKCircuit storage circuit = circuits[name];
        circuit.name = name;
        circuit.description = description;
        circuit.creator = msg.sender;
        circuit.vk = vk;
        circuit.isActive = true;
        circuit.createdTime = block.timestamp;
        circuit.verificationCount = 0;

        circuitNames.push(name);

        emit CircuitRegistered(name, msg.sender);
    }

    /**
     * @dev Verify a ZK proof
     * @param circuitName Name of the circuit to use
     * @param proof ZK proof to verify
     * @param publicInputs Public inputs for the proof
     * @return Whether the proof is valid
     */
    function verifyProof(
        string memory circuitName,
        ZKProof memory proof,
        uint256[] memory publicInputs
    ) external payable circuitExists(circuitName) circuitActive(circuitName) validProof(proof) nonReentrant returns (bool) {
        require(msg.value >= verificationFee, "Insufficient verification fee");
        
        uint256 gasStart = gasleft();
        bytes32 proofHash = keccak256(abi.encode(proof, publicInputs));
        
        // Check if proof was already used
        require(!circuits[circuitName].usedProofs[proofHash], "Proof already used");
        
        // Perform ZK-SNARK verification (simplified - in production would use actual pairing)
        bool isValid = _performVerification(circuitName, proof, publicInputs);
        
        // Record verification
        VerificationRecord memory record = VerificationRecord({
            proofHash: proofHash,
            verifier: msg.sender,
            timestamp: block.timestamp,
            isValid: isValid,
            circuitName: circuitName,
            gasUsed: gasStart - gasleft()
        });
        
        proofRecords[proofHash] = record;
        userVerifications[msg.sender].push(record);
        
        if (isValid) {
            circuits[circuitName].usedProofs[proofHash] = true;
            circuits[circuitName].verificationCount++;
        }
        
        // Refund excess fee
        if (msg.value > verificationFee) {
            payable(msg.sender).transfer(msg.value - verificationFee);
        }
        
        emit ProofVerified(proofHash, msg.sender, isValid);
        return isValid;
    }

    /**
     * @dev Batch verify multiple proofs
     * @param circuitName Name of the circuit
     * @param proofs Array of proofs to verify
     * @param publicInputsArray Array of public inputs arrays
     * @return Array of verification results
     */
    function batchVerifyProofs(
        string memory circuitName,
        ZKProof[] memory proofs,
        uint256[][] memory publicInputsArray
    ) external payable circuitExists(circuitName) circuitActive(circuitName) returns (bool[] memory) {
        require(proofs.length == publicInputsArray.length, "Arrays length mismatch");
        require(msg.value >= verificationFee * proofs.length, "Insufficient batch verification fee");
        
        bool[] memory results = new bool[](proofs.length);
        
        for (uint256 i = 0; i < proofs.length; i++) {
            require(proofs[i].a.length == 2, "Invalid proof A");
            require(proofs[i].b.length == 2, "Invalid proof B");
            require(proofs[i].c.length == 2, "Invalid proof C");
            
            bytes32 proofHash = keccak256(abi.encode(proofs[i], publicInputsArray[i]));
            require(!circuits[circuitName].usedProofs[proofHash], "Proof already used");
            
            results[i] = _performVerification(circuitName, proofs[i], publicInputsArray[i]);
            
            if (results[i]) {
                circuits[circuitName].usedProofs[proofHash] = true;
                circuits[circuitName].verificationCount++;
            }
            
            // Record verification
            VerificationRecord memory record = VerificationRecord({
                proofHash: proofHash,
                verifier: msg.sender,
                timestamp: block.timestamp,
                isValid: results[i],
                circuitName: circuitName,
                gasUsed: 0 // Simplified for batch
            });
            
            proofRecords[proofHash] = record;
            userVerifications[msg.sender].push(record);
            
            emit ProofVerified(proofHash, msg.sender, results[i]);
        }
        
        // Refund excess fee
        uint256 requiredFee = verificationFee * proofs.length;
        if (msg.value > requiredFee) {
            payable(msg.sender).transfer(msg.value - requiredFee);
        }
        
        return results;
    }

    /**
     * @dev Get circuit information
     * @param circuitName Circuit name
     * @return Circuit details
     */
    function getCircuitInfo(string memory circuitName) external view circuitExists(circuitName) returns (
        string memory name,
        string memory description,
        address creator,
        bool isActive,
        uint256 createdTime,
        uint256 verificationCount
    ) {
        ZKCircuit storage circuit = circuits[circuitName];
        return (
            circuit.name,
            circuit.description,
            circuit.creator,
            circuit.isActive,
            circuit.createdTime,
            circuit.verificationCount
        );
    }

    /**
     * @dev Get user verification history
     * @param user User address
     * @return Array of verification records
     */
    function getUserVerifications(address user) external view returns (VerificationRecord[] memory) {
        return userVerifications[user];
    }

    /**
     * @dev Get all circuit names
     * @return Array of circuit names
     */
    function getCircuitNames() external view returns (string[] memory) {
        return circuitNames;
    }

    /**
     * @dev Update circuit status
     * @param circuitName Circuit name
     * @param isActive Active status
     */
    function updateCircuitStatus(string memory circuitName, bool isActive) external onlyOwner circuitExists(circuitName) {
        circuits[circuitName].isActive = isActive;
        emit CircuitUpdated(circuitName, isActive);
    }

    /**
     * @dev Update verification fee
     * @param newFee New verification fee
     */
    function updateVerificationFee(uint256 newFee) external onlyOwner {
        verificationFee = newFee;
        emit VerificationFeeUpdated(newFee);
    }

    /**
     * @dev Pause verification operations
     */
    function pause() external onlyOwner {
        _pause();
    }

    /**
     * @dev Unpause verification operations
     */
    function unpause() external onlyOwner {
        _unpause();
    }

    /**
     * @dev Internal verification function (simplified)
     * @param circuitName Circuit name
     * @param proof ZK proof
     * @param publicInputs Public inputs
     * @return Whether verification succeeded
     */
    function _performVerification(
        string memory circuitName,
        ZKProof memory proof,
        uint256[] memory publicInputs
    ) internal view returns (bool) {
        // Simplified verification - in production would use actual pairing checks
        // This is a placeholder for the actual ZK-SNARK verification algorithm
        
        // Basic checks
        if (proof.a[0] == 0 || proof.a[1] == 0) return false;
        if (proof.b[0][0] == 0 || proof.b[0][1] == 0) return false;
        if (proof.b[1][0] == 0 || proof.b[1][1] == 0) return false;
        if (proof.c[0] == 0 || proof.c[1] == 0) return false;
        
        // Simulate verification with basic validation
        // In reality, this would involve complex elliptic curve pairings
        return true;
    }

    /**
     * @dev Get verification statistics
     * @return Total verifications, active circuits, total fees collected
     */
    function getVerificationStats() external view returns (
        uint256 totalVerifications,
        uint256 activeCircuits,
        uint256 totalFees
    ) {
        uint256 total = 0;
        uint256 active = 0;
        
        for (uint256 i = 0; i < circuitNames.length; i++) {
            ZKCircuit storage circuit = circuits[circuitNames[i]];
            total = total.add(circuit.verificationCount);
            if (circuit.isActive) {
                active++;
            }
        }
        
        return (total, active, address(this).balance);
    }

    /**
     * @dev Check if a proof has been used
     * @param circuitName Circuit name
     * @param proofHash Hash of the proof
     * @return Whether the proof has been used
     */
    function isProofUsed(string memory circuitName, bytes32 proofHash) external view circuitExists(circuitName) returns (bool) {
        return circuits[circuitName].usedProofs[proofHash];
    }

    /**
     * @dev Withdraw collected fees
     */
    function withdrawFees() external onlyOwner {
        uint256 balance = address(this).balance;
        require(balance > 0, "No fees to withdraw");
        payable(owner()).transfer(balance);
    }

    /**
     * @dev Create a privacy-preserving proof for age verification
     * @param proof ZK proof
     * @param publicInputs Public inputs (age commitment, etc.)
     * @return Whether the age verification is valid
     */
    function verifyAgeProof(
        ZKProof memory proof,
        uint256[] memory publicInputs
    ) external payable returns (bool) {
        return this.verifyProof("age_verification", proof, publicInputs);
    }

    /**
     * @dev Create a privacy-preserving proof for identity verification
     * @param proof ZK proof
     * @param publicInputs Public inputs (identity commitment, etc.)
     * @return Whether the identity verification is valid
     */
    function verifyIdentityProof(
        ZKProof memory proof,
        uint256[] memory publicInputs
    ) external payable returns (bool) {
        return this.verifyProof("identity_verification", proof, publicInputs);
    }

    /**
     * @dev Create a privacy-preserving proof for financial verification
     * @param proof ZK proof
     * @param publicInputs Public inputs (financial commitment, etc.)
     * @return Whether the financial verification is valid
     */
    function verifyFinancialProof(
        ZKProof memory proof,
        uint256[] memory publicInputs
    ) external payable returns (bool) {
        return this.verifyProof("financial_verification", proof, publicInputs);
    }
}
