#![no_std]

use soroban_sdk::{
    contract, contracterror, contractimpl, contracttype, symbol_short, Address, Env, String
};

#[contracterror]
#[derive(Copy, Clone, Debug, Eq, PartialEq, PartialOrd, Ord)]
#[repr(u32)]
pub enum RegistryError {
    AlreadyInitialized = 1,
    NotInitialized = 2,
    Unauthorized = 3,
    EntryAlreadyExists = 4,
    EntryNotFound = 5,
}

#[contracttype]
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct FoodEntry {
    pub classification: String,
    pub confidence: u32,
    pub timestamp: u64,
    pub verifier: Address,
}

#[contracttype]
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum DataKey {
    Admin,
    Entry(String),
}

#[contract]
pub struct FoodRegistryContract;

#[contractimpl]
impl FoodRegistryContract {
    pub fn initialize(env: Env, admin: Address) -> Result<(), RegistryError> {
        if env.storage().persistent().has(&DataKey::Admin) {
            return Err(RegistryError::AlreadyInitialized);
        }
        env.storage().persistent().set(&DataKey::Admin, &admin);
        Ok(())
    }

    pub fn register_food_entry(
        env: Env,
        image_hash: String,
        classification: String,
        confidence: u32,
    ) -> Result<(), RegistryError> {
        let admin: Address = env.storage().persistent().get(&DataKey::Admin)
            .ok_or(RegistryError::NotInitialized)?;
        
        admin.require_auth();

        let key = DataKey::Entry(image_hash.clone());
        if env.storage().persistent().has(&key) {
            return Err(RegistryError::EntryAlreadyExists);
        }

        let entry = FoodEntry {
            classification: classification.clone(),
            confidence,
            timestamp: env.ledger().timestamp(),
            verifier: admin,
        };

        env.storage().persistent().set(&key, &entry);

        env.events().publish(
            (symbol_short!("new_ent"), image_hash), 
            classification
        );

        Ok(())
    }

    pub fn get_food_entry(env: Env, image_hash: String) -> Result<FoodEntry, RegistryError> {
        let key = DataKey::Entry(image_hash);
        env.storage().persistent().get(&key).ok_or(RegistryError::EntryNotFound)
    }
}

#[cfg(test)]
mod test;
