// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/utils/math/SafeMath.sol";

/**
 * @title AdvancedOracle
 * @dev Advanced oracle system for real-world data integration and validation
 * @notice This contract provides a comprehensive oracle solution with reputation system,
 * cost optimization, and security implementations
 */
contract AdvancedOracle is Ownable, ReentrancyGuard, Pausable {
    using SafeMath for uint256;

    // Oracle data structures
    struct Oracle {
        address provider;
        string name;
        uint256 reputation;
        uint256 totalRequests;
        uint256 successfulRequests;
        uint256 fee;
        bool isActive;
        uint256 lastUpdateTime;
        mapping(string => uint256) dataPoints; // dataPointId => value
        string[] supportedDataTypes;
    }

    struct DataRequest {
        uint256 id;
        address requester;
        string dataType;
        uint256 deadline;
        uint256 bounty;
        uint256 minReputation;
        bool fulfilled;
        uint256 responseTime;
        bytes32 dataHash;
        address selectedOracle;
    }

    struct ValidationReport {
        uint256 requestId;
        address validator;
        bool isValid;
        string reason;
        uint256 timestamp;
    }

    // State variables
    mapping(address => Oracle) public oracles;
    mapping(uint256 => DataRequest) public dataRequests;
    mapping(uint256 => ValidationReport[]) public validationReports;
    mapping(string => address[]) public dataTypeToOracles;
    
    address[] public oracleProviders;
    uint256 public requestCounter;
    uint256 public validationRewardPercentage = 5; // 5% of bounty goes to validators
    uint256 public minReputationThreshold = 50;
    
    // Events
    event OracleRegistered(address indexed provider, string name, uint256 fee);
    event OracleUpdated(address indexed provider, uint256 reputation, bool isActive);
    event DataRequested(uint256 indexed requestId, address indexed requester, string dataType, uint256 bounty);
    event DataProvided(uint256 indexed requestId, address indexed oracle, bytes32 dataHash);
    event ValidationSubmitted(uint256 indexed requestId, address indexed validator, bool isValid);
    event OracleReputationUpdated(address indexed oracle, uint256 newReputation);

    // Modifiers
    modifier onlyActiveOracle() {
        require(oracles[msg.sender].isActive, "Oracle is not active");
        _;
    }

    modifier validRequestId(uint256 _requestId) {
        require(_requestId < requestCounter, "Invalid request ID");
        _;
    }

    /**
     * @dev Register a new oracle provider
     * @param _name Oracle provider name
     * @param _fee Fee per data request
     * @param _supportedDataTypes Array of supported data types
     */
    function registerOracle(
        string memory _name,
        uint256 _fee,
        string[] memory _supportedDataTypes
    ) external {
        require(oracles[msg.sender].provider == address(0), "Oracle already registered");
        require(_fee > 0, "Fee must be greater than 0");
        require(_supportedDataTypes.length > 0, "Must support at least one data type");

        Oracle storage oracle = oracles[msg.sender];
        oracle.provider = msg.sender;
        oracle.name = _name;
        oracle.reputation = 100; // Start with perfect reputation
        oracle.fee = _fee;
        oracle.isActive = true;
        oracle.lastUpdateTime = block.timestamp;
        oracle.supportedDataTypes = _supportedDataTypes;

        oracleProviders.push(msg.sender);

        // Update data type mappings
        for (uint i = 0; i < _supportedDataTypes.length; i++) {
            dataTypeToOracles[_supportedDataTypes[i]].push(msg.sender);
        }

        emit OracleRegistered(msg.sender, _name, _fee);
    }

    /**
     * @dev Request data from oracles
     * @param _dataType Type of data requested
     * @param _deadline Deadline for data provision
     * @param _bounty Bounty amount for successful data provision
     * @param _minReputation Minimum reputation requirement
     */
    function requestData(
        string memory _dataType,
        uint256 _deadline,
        uint256 _bounty,
        uint256 _minReputation
    ) external payable nonReentrant whenNotPaused {
        require(msg.value >= _bounty, "Insufficient bounty amount");
        require(_deadline > block.timestamp, "Deadline must be in future");
        require(_bounty > 0, "Bounty must be greater than 0");
        require(dataTypeToOracles[_dataType].length > 0, "No oracles support this data type");

        DataRequest storage request = dataRequests[requestCounter];
        request.id = requestCounter;
        request.requester = msg.sender;
        request.dataType = _dataType;
        request.deadline = _deadline;
        request.bounty = _bounty;
        request.minReputation = _minReputation;
        request.fulfilled = false;

        emit DataRequested(requestCounter, msg.sender, _dataType, _bounty);
        requestCounter++;
    }

    /**
     * @dev Provide data for a request
     * @param _requestId Request ID
     * @param _dataHash Hash of the provided data
     * @param _value Actual data value (for on-chain storage)
     */
    function provideData(
        uint256 _requestId,
        bytes32 _dataHash,
        uint256 _value
    ) external onlyActiveOracle validRequestId(_requestId) nonReentrant {
        DataRequest storage request = dataRequests[_requestId];
        require(!request.fulfilled, "Request already fulfilled");
        require(block.timestamp <= request.deadline, "Request deadline passed");
        require(oracles[msg.sender].reputation >= request.minReputation, "Insufficient reputation");

        Oracle storage oracle = oracles[msg.sender];
        require(oracle.fee <= request.bounty, "Oracle fee exceeds bounty");

        // Update request
        request.fulfilled = true;
        request.responseTime = block.timestamp;
        request.dataHash = _dataHash;
        request.selectedOracle = msg.sender;

        // Store data point
        oracle.dataPoints[request.dataType] = _value;

        // Update oracle statistics
        oracle.totalRequests++;
        oracle.successfulRequests++;
        oracle.lastUpdateTime = block.timestamp;

        // Payment to oracle
        uint256 payment = request.bounty.sub(oracle.fee);
        payable(msg.sender).transfer(request.bounty);

        emit DataProvided(_requestId, msg.sender, _dataHash);
    }

    /**
     * @dev Submit validation report for provided data
     * @param _requestId Request ID
     * @param _isValid Whether the data is valid
     * @param _reason Validation reason
     */
    function submitValidation(
        uint256 _requestId,
        bool _isValid,
        string memory _reason
    ) external validRequestId(_requestId) {
        DataRequest storage request = dataRequests[_requestId];
        require(request.fulfilled, "Request not yet fulfilled");
        require(block.timestamp <= request.deadline.add(1 days), "Validation period expired");

        ValidationReport memory report = ValidationReport({
            requestId: _requestId,
            validator: msg.sender,
            isValid: _isValid,
            reason: _reason,
            timestamp: block.timestamp
        });

        validationReports[_requestId].push(report);

        // Update oracle reputation based on validation
        if (!_isValid) {
            _updateOracleReputation(request.selectedOracle, -10);
        } else {
            _updateOracleReputation(request.selectedOracle, 5);
        }

        emit ValidationSubmitted(_requestId, msg.sender, _isValid);
    }

    /**
     * @dev Get available oracles for a specific data type
     * @param _dataType Data type
     * @return Array of oracle addresses
     */
    function getAvailableOracles(string memory _dataType) external view returns (address[] memory) {
        return dataTypeToOracles[_dataType];
    }

    /**
     * @dev Get oracle statistics
     * @param _oracle Oracle address
     * @return reputation, totalRequests, successfulRequests, fee, isActive
     */
    function getOracleStats(address _oracle) external view returns (
        uint256 reputation,
        uint256 totalRequests,
        uint256 successfulRequests,
        uint256 fee,
        bool isActive
    ) {
        Oracle storage oracle = oracles[_oracle];
        return (
            oracle.reputation,
            oracle.totalRequests,
            oracle.successfulRequests,
            oracle.fee,
            oracle.isActive
        );
    }

    /**
     * @dev Update oracle fee
     * @param _newFee New fee amount
     */
    function updateFee(uint256 _newFee) external onlyActiveOracle {
        require(_newFee > 0, "Fee must be greater than 0");
        oracles[msg.sender].fee = _newFee;
        oracles[msg.sender].lastUpdateTime = block.timestamp;
    }

    /**
     * @dev Pause oracle operations (emergency only)
     */
    function pauseOracle() external onlyOwner {
        _pause();
    }

    /**
     * @dev Unpause oracle operations
     */
    function unpauseOracle() external onlyOwner {
        _unpause();
    }

    /**
     * @dev Update minimum reputation threshold
     * @param _newThreshold New threshold
     */
    function updateMinReputationThreshold(uint256 _newThreshold) external onlyOwner {
        minReputationThreshold = _newThreshold;
    }

    /**
     * @dev Internal function to update oracle reputation
     * @param _oracle Oracle address
     * @param _change Reputation change (can be negative)
     */
    function _updateOracleReputation(address _oracle, int256 _change) internal {
        Oracle storage oracle = oracles[_oracle];
        if (_change > 0) {
            oracle.reputation = oracle.reputation.add(uint256(_change));
        } else {
            uint256 decrease = uint256(-_change);
            if (decrease >= oracle.reputation) {
                oracle.reputation = 0;
                oracle.isActive = false; // Deactivate if reputation drops to 0
            } else {
                oracle.reputation = oracle.reputation.sub(decrease);
            }
        }
        emit OracleReputationUpdated(_oracle, oracle.reputation);
    }

    /**
     * @dev Get success rate for an oracle
     * @param _oracle Oracle address
     * @return Success rate as percentage (0-100)
     */
    function getOracleSuccessRate(address _oracle) external view returns (uint256) {
        Oracle storage oracle = oracles[_oracle];
        if (oracle.totalRequests == 0) return 0;
        return oracle.successfulRequests.mul(100).div(oracle.totalRequests);
    }

    /**
     * @dev Get data point value from oracle
     * @param _oracle Oracle address
     * @param _dataPointId Data point identifier
     * @return Data point value
     */
    function getDataPoint(address _oracle, string memory _dataPointId) external view returns (uint256) {
        return oracles[_oracle].dataPoints[_dataPointId];
    }
}
