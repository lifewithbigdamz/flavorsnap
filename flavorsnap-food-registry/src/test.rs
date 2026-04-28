#[cfg(test)]
use super::*;
use soroban_sdk::{testutils::Address as _, Address, Env, String};

#[test]
fn test_food_registry_flow() {
    let env = Env::default();
    env.mock_all_auths();

    let contract_id = env.register(FoodRegistryContract, ());
    let client = FoodRegistryContractClient::new(&env, &contract_id);

    let admin = Address::generate(&env);
    client.initialize(&admin);

    let img_hash = String::from_str(&env, "abc123hash");
    let dish = String::from_str(&env, "Sushi");
    client.register_food_entry(&img_hash, &dish, &95);

    let entry = client.get_food_entry(&img_hash);
    assert_eq!(entry.classification, dish);
    assert_eq!(entry.confidence, 95);
    assert_eq!(entry.verifier, admin);

    let res = client.try_register_food_entry(&img_hash, &dish, &95);
    assert!(res.is_err());
}
