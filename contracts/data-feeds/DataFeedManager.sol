// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/utils/math/SafeMath.sol";

/**
 * @title DataFeedManager
 * @dev Manages multiple data feeds with aggregation and validation
 * @notice This contract provides a comprehensive data feed management system
 */
contract DataFeedManager is Ownable, ReentrancyGuard, Pausable {
    using SafeMath for uint256;

    struct DataFeed {
        string name;
        string description;
        uint256 updateInterval;
        uint256 lastUpdateTime;
        uint256 value;
        uint256 decimals;
        bool isActive;
        address[] validators;
        mapping(address => bool) isValidator;
        uint256 validationThreshold;
    }

    struct DataPoint {
        uint256 timestamp;
        uint256 value;
        address provider;
        uint256 confidence;
    }

    mapping(string => DataFeed) public dataFeeds;
    mapping(string => DataPoint[]) public dataHistory;
    string[] public feedNames;

    uint256 public maxHistoryLength = 1000;
    uint256 public defaultValidationThreshold = 51; // 51% consensus required

    event DataFeedCreated(string indexed name, string description, uint256 updateInterval);
    event DataUpdated(string indexed feedName, uint256 value, address indexed provider);
    event ValidatorAdded(string indexed feedName, address indexed validator);
    event ValidatorRemoved(string indexed feedName, address indexed validator);

    modifier onlyFeedValidator(string memory feedName) {
        require(dataFeeds[feedName].isValidator[msg.sender], "Not a validator for this feed");
        _;
    }

    modifier feedExists(string memory feedName) {
        require(bytes(dataFeeds[feedName].name).length > 0, "Data feed does not exist");
        _;
    }

    /**
     * @dev Create a new data feed
     * @param name Feed name
     * @param description Feed description
     * @param updateInterval Update interval in seconds
     * @param decimals Number of decimal places
     * @param validationThreshold Consensus threshold percentage
     */
    function createDataFeed(
        string memory name,
        string memory description,
        uint256 updateInterval,
        uint256 decimals,
        uint256 validationThreshold
    ) external onlyOwner {
        require(bytes(name).length > 0, "Name cannot be empty");
        require(updateInterval > 0, "Update interval must be positive");
        require(validationThreshold > 0 && validationThreshold <= 100, "Invalid threshold");

        DataFeed storage feed = dataFeeds[name];
        feed.name = name;
        feed.description = description;
        feed.updateInterval = updateInterval;
        feed.lastUpdateTime = 0;
        feed.value = 0;
        feed.decimals = decimals;
        feed.isActive = true;
        feed.validationThreshold = validationThreshold;

        feedNames.push(name);

        emit DataFeedCreated(name, description, updateInterval);
    }

    /**
     * @dev Update data feed value
     * @param feedName Feed name
     * @param value New value
     * @param confidence Confidence score (0-100)
     */
    function updateDataFeed(
        string memory feedName,
        uint256 value,
        uint256 confidence
    ) external feedExists(feedName) returns (bool) {
        DataFeed storage feed = dataFeeds[feedName];
        require(feed.isActive, "Feed is not active");
        require(block.timestamp >= feed.lastUpdateTime.add(feed.updateInterval), "Update interval not met");
        require(confidence <= 100, "Confidence must be <= 100");

        // Add to history
        dataHistory[feedName].push(DataPoint({
            timestamp: block.timestamp,
            value: value,
            provider: msg.sender,
            confidence: confidence
        }));

        // Trim history if too long
        if (dataHistory[feedName].length > maxHistoryLength) {
            for (uint256 i = 0; i < 10; i++) {
                // Remove first 10 elements
                for (uint256 j = 0; j < dataHistory[feedName].length - 1; j++) {
                    dataHistory[feedName][j] = dataHistory[feedName][j + 1];
                }
                dataHistory[feedName].pop();
            }
        }

        // Update feed value if validation passes
        if (_validateDataUpdate(feedName, value)) {
            feed.value = value;
            feed.lastUpdateTime = block.timestamp;
            emit DataUpdated(feedName, value, msg.sender);
            return true;
        }

        return false;
    }

    /**
     * @dev Add validator to data feed
     * @param feedName Feed name
     * @param validator Validator address
     */
    function addValidator(
        string memory feedName,
        address validator
    ) external onlyOwner feedExists(feedName) {
        DataFeed storage feed = dataFeeds[feedName];
        require(!feed.isValidator[validator], "Already a validator");

        feed.validators.push(validator);
        feed.isValidator[validator] = true;

        emit ValidatorAdded(feedName, validator);
    }

    /**
     * @dev Remove validator from data feed
     * @param feedName Feed name
     * @param validator Validator address
     */
    function removeValidator(
        string memory feedName,
        address validator
    ) external onlyOwner feedExists(feedName) {
        DataFeed storage feed = dataFeeds[feedName];
        require(feed.isValidator[validator], "Not a validator");

        feed.isValidator[validator] = false;
        
        // Remove from validators array
        for (uint256 i = 0; i < feed.validators.length; i++) {
            if (feed.validators[i] == validator) {
                feed.validators[i] = feed.validators[feed.validators.length - 1];
                feed.validators.pop();
                break;
            }
        }

        emit ValidatorRemoved(feedName, validator);
    }

    /**
     * @dev Get aggregated value from multiple oracles
     * @param feedName Feed name
     * @return Aggregated value
     */
    function getAggregatedValue(string memory feedName) external view feedExists(feedName) returns (uint256) {
        return dataFeeds[feedName].value;
    }

    /**
     * @dev Get historical data points
     * @param feedName Feed name
     * @param limit Maximum number of points to return
     * @return Array of data points
     */
    function getHistoricalData(
        string memory feedName,
        uint256 limit
    ) external view feedExists(feedName) returns (DataPoint[] memory) {
        DataPoint[] storage history = dataHistory[feedName];
        uint256 length = history.length > limit ? limit : history.length;
        
        DataPoint[] memory result = new DataPoint[](length);
        for (uint256 i = 0; i < length; i++) {
            result[i] = history[history.length - length + i];
        }
        
        return result;
    }

    /**
     * @dev Validate data update using consensus
     * @param feedName Feed name
     * @param value Proposed value
     * @return Whether the update is valid
     */
    function _validateDataUpdate(
        string memory feedName,
        uint256 value
    ) internal view returns (bool) {
        DataFeed storage feed = dataFeeds[feedName];
        
        // If no validators, accept the update
        if (feed.validators.length == 0) {
            return true;
        }

        // Check recent data points for consensus
        DataPoint[] storage history = dataHistory[feedName];
        if (history.length < 3) {
            return true; // Not enough data for consensus
        }

        uint256 validCount = 0;
        uint256 totalWeight = 0;
        
        // Check last 10 data points
        uint256 start = history.length > 10 ? history.length - 10 : 0;
        for (uint256 i = start; i < history.length; i++) {
            DataPoint memory point = history[i];
            
            // Calculate deviation from proposed value
            uint256 deviation = point.value > value ? 
                point.value.sub(value) : value.sub(point.value);
            uint256 maxDeviation = point.value.mul(10).div(100); // 10% tolerance
            
            if (deviation <= maxDeviation) {
                validCount = validCount.add(point.confidence);
            }
            totalWeight = totalWeight.add(point.confidence);
        }

        if (totalWeight == 0) return true;
        
        uint256 consensusPercentage = validCount.mul(100).div(totalWeight);
        return consensusPercentage >= feed.validationThreshold;
    }

    /**
     * @dev Get feed statistics
     * @param feedName Feed name
     * @return Various statistics about the feed
     */
    function getFeedStats(string memory feedName) external view feedExists(feedName) returns (
        uint256 value,
        uint256 lastUpdateTime,
        uint256 updateInterval,
        uint256 decimals,
        bool isActive,
        uint256 validatorCount,
        uint256 dataPointCount
    ) {
        DataFeed storage feed = dataFeeds[feedName];
        return (
            feed.value,
            feed.lastUpdateTime,
            feed.updateInterval,
            feed.decimals,
            feed.isActive,
            feed.validators.length,
            dataHistory[feedName].length
        );
    }

    /**
     * @dev Pause data feed operations
     */
    function pause() external onlyOwner {
        _pause();
    }

    /**
     * @dev Unpause data feed operations
     */
    function unpause() external onlyOwner {
        _unpause();
    }

    /**
     * @dev Update feed status
     * @param feedName Feed name
     * @param isActive Active status
     */
    function setFeedStatus(string memory feedName, bool isActive) external onlyOwner feedExists(feedName) {
        dataFeeds[feedName].isActive = isActive;
    }

    /**
     * @dev Update validation threshold
     * @param feedName Feed name
     * @param threshold New threshold
     */
    function setValidationThreshold(string memory feedName, uint256 threshold) external onlyOwner feedExists(feedName) {
        require(threshold > 0 && threshold <= 100, "Invalid threshold");
        dataFeeds[feedName].validationThreshold = threshold;
    }

    /**
     * @dev Get all feed names
     * @return Array of feed names
     */
    function getFeedNames() external view returns (string[] memory) {
        return feedNames;
    }

    /**
     * @dev Calculate median value from recent data points
     * @param feedName Feed name
     * @return Median value
     */
    function getMedianValue(string memory feedName) external view feedExists(feedName) returns (uint256) {
        DataPoint[] storage history = dataHistory[feedName];
        if (history.length == 0) return 0;
        
        uint256 length = history.length > 10 ? 10 : history.length;
        uint256[] memory values = new uint256[](length);
        
        for (uint256 i = 0; i < length; i++) {
            values[i] = history[history.length - length + i].value;
        }
        
        // Simple median calculation
        for (uint256 i = 0; i < length; i++) {
            for (uint256 j = i + 1; j < length; j++) {
                if (values[i] > values[j]) {
                    uint256 temp = values[i];
                    values[i] = values[j];
                    values[j] = temp;
                }
            }
        }
        
        return values[length / 2];
    }
}
