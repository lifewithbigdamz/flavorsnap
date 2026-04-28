#![cfg(test)]

use super::*;
use soroban_sdk::{testutils::{Address as _, Ledger}, token, Env, String};

#[test]
fn test_license_purchase_flow() {
    let env = Env::default();
    
    env.ledger().with_mut(|li| {
        li.timestamp = 12345;
    });

    // 1. Register Contract
    let contract_address = env.register(IPLicensingContract, ());
    let client = IPLicensingContractClient::new(&env, &contract_address);

    // 2. Setup Token & Admin
    let token_admin = Address::generate(&env);
    let sac = env.register_stellar_asset_contract_v2(token_admin.clone());
    let token_address = sac.address();
    
    let token_admin_client = token::StellarAssetClient::new(&env, &token_address);
    let token_client = token::Client::new(&env, &token_address);

    let owner = Address::generate(&env);
    let buyer = Address::generate(&env);

    // 3. Mint tokens (Must mock auth!)
    token_admin_client.mock_all_auths().mint(&buyer, &1000);
    assert_eq!(token_client.balance(&buyer), 1000);

    // 4. Register IP (Must mock auth for owner!)
    client.mock_all_auths().register_ip(
        &owner,
        &101, 
        &String::from_str(&env, "ipfs://metadata"),
        &500,
        &100,
        &token_address
    );

    // 5. Purchase License (Must mock auth for buyer!)
    client.mock_all_auths().purchase_license(
        &buyer, 
        &101, 
        &LicenseType::NonExclusive
    );

    // 6. Verify Balances
    assert_eq!(token_client.balance(&buyer), 900);
    assert_eq!(token_client.balance(&owner), 100);

    // 7. Verify Exclusive Restriction
    // We expect this to fail, so we dont necessarily need mock_auths here if it fails early,
    // but good practice to include it if the failure is logic-based.
    // However, try_purchase_license captures the error.
    let res = client.mock_all_auths().try_purchase_license(&buyer, &101, &LicenseType::Exclusive);
    assert!(res.is_err()); 
}
