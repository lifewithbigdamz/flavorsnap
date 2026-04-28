pragma circom 2.0.0;

include "circomlib/circuits/comparators.circom";
include "circomlib/circuits/bitify.circom";
include "circomlib/circuits/poseidon.circom";

/**
 * @title AgeVerification
 * @dev Zero-knowledge circuit for age verification without revealing actual age
 * @notice This circuit allows proving that a person is above a certain age without revealing their exact age
 */
template AgeVerification() {
    // Private inputs
    signal input actualAge;
    signal input salt;
    
    // Public inputs
    signal input minAge;
    signal input ageCommitment;
    
    // Output
    signal output isAboveMinAge;
    
    // Components
    component ageHash = Poseidon(2);
    component ageComparator = GreaterEqThan(8);
    
    // Compute age commitment
    ageHash.inputs[0] <== actualAge;
    ageHash.inputs[1] <== salt;
    
    // Verify commitment matches
    ageCommitment === ageHash.out;
    
    // Compare age with minimum age
    ageComparator.in[0] <== actualAge;
    ageComparator.in[1] <== minAge;
    
    // Output result
    isAboveMinAge <== ageComparator.out;
}

component main = AgeVerification();
