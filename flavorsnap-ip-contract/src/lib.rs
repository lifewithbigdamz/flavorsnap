#![no_std]

use soroban_sdk::{
    contract, contracterror, contractimpl, contracttype, token, Address, Env, String
};

#[contracterror]
#[derive(Copy, Clone, Debug, Eq, PartialEq, PartialOrd, Ord)]
#[repr(u32)]
pub enum IPError {
    Unauthorized = 1,
    IPAlreadyRegistered = 2,
    IPNotFound = 3,
    ExclusiveAlreadyIssued = 4,
    ActiveLicensesExist = 5,
    LicenseNotFound = 6,
    LicenseAlreadyExists = 7,
}

#[contracttype]
#[derive(Copy, Clone, Debug, Eq, PartialEq)]
pub enum LicenseType {
    Exclusive,
    NonExclusive,
}

#[contracttype]
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct IPAsset {
    pub owner: Address,
    pub metadata_uri: String,
    pub price_exclusive: i128,
    pub price_non_exclusive: i128,
    pub payment_token: Address,
    pub has_exclusive: bool,
    pub active_licenses: u32,
}

#[contracttype]
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct License {
    pub licensee: Address,
    pub ip_id: u64,
    pub license_type: LicenseType,
    pub is_active: bool,
}

#[contracttype]
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum DataKey {
    IP(u64),
    License(u64, Address),
}

#[contract]
pub struct IPLicensingContract;

#[contractimpl]
impl IPLicensingContract {
    /// Register a new IP asset
    pub fn register_ip(
        env: Env,
        owner: Address,
        ip_id: u64,
        metadata_uri: String,
        price_exclusive: i128,
        price_non_exclusive: i128,
        payment_token: Address,
    ) -> Result<(), IPError> {
        owner.require_auth();

        let key = DataKey::IP(ip_id);
        if env.storage().persistent().has(&key) {
            return Err(IPError::IPAlreadyRegistered);
        }

        let asset = IPAsset {
            owner,
            metadata_uri,
            price_exclusive,
            price_non_exclusive,
            payment_token,
            has_exclusive: false,
            active_licenses: 0,
        };

        env.storage().persistent().set(&key, &asset);
        Ok(())
    }

    /// Purchase a license
    pub fn purchase_license(
        env: Env,
        licensee: Address,
        ip_id: u64,
        license_type: LicenseType,
    ) -> Result<(), IPError> {
        licensee.require_auth();

        let ip_key = DataKey::IP(ip_id);
        let mut ip: IPAsset = env.storage().persistent().get(&ip_key).ok_or(IPError::IPNotFound)?;

        // Validation: Exclusive logic
        if ip.has_exclusive {
            return Err(IPError::ExclusiveAlreadyIssued);
        }
        if license_type == LicenseType::Exclusive && ip.active_licenses > 0 {
            return Err(IPError::ActiveLicensesExist);
        }

        let license_key = DataKey::License(ip_id, licensee.clone());
        if env.storage().persistent().has(&license_key) {
            let existing_license: License = env.storage().persistent().get(&license_key).unwrap();
            if existing_license.is_active {
                return Err(IPError::LicenseAlreadyExists);
            }
        }

        // Determine price
        let price = match license_type {
            LicenseType::Exclusive => ip.price_exclusive,
            LicenseType::NonExclusive => ip.price_non_exclusive,
        };

        // Execute Payment
        let token_client = token::Client::new(&env, &ip.payment_token);
        token_client.transfer(&licensee, &ip.owner, &price);

        // Update State
        if license_type == LicenseType::Exclusive {
            ip.has_exclusive = true;
        } else {
            ip.active_licenses += 1;
        }
        
        env.storage().persistent().set(&ip_key, &ip);

        let new_license = License {
            licensee: licensee.clone(),
            ip_id,
            license_type,
            is_active: true,
        };
        env.storage().persistent().set(&license_key, &new_license);

        Ok(())
    }

    /// Pay usage-based royalties
    pub fn pay_usage_royalty(
        env: Env,
        licensee: Address,
        ip_id: u64,
        amount: i128,
    ) -> Result<(), IPError> {
        licensee.require_auth();
        
        let ip_key = DataKey::IP(ip_id);
        let ip: IPAsset = env.storage().persistent().get(&ip_key).ok_or(IPError::IPNotFound)?;

        let license_key = DataKey::License(ip_id, licensee.clone());
        let license: License = env.storage().persistent().get(&license_key).ok_or(IPError::LicenseNotFound)?;

        if !license.is_active {
            return Err(IPError::LicenseNotFound);
        }

        let token_client = token::Client::new(&env, &ip.payment_token);
        token_client.transfer(&licensee, &ip.owner, &amount);

        Ok(())
    }

    /// Revoke an active license (Only callable by IP owner)
    pub fn revoke_license(
        env: Env,
        owner: Address,
        licensee: Address,
        ip_id: u64,
    ) -> Result<(), IPError> {
        owner.require_auth();

        let ip_key = DataKey::IP(ip_id);
        let mut ip: IPAsset = env.storage().persistent().get(&ip_key).ok_or(IPError::IPNotFound)?;

        if ip.owner != owner {
            return Err(IPError::Unauthorized);
        }

        let license_key = DataKey::License(ip_id, licensee.clone());
        let mut license: License = env.storage().persistent().get(&license_key).ok_or(IPError::LicenseNotFound)?;

        if !license.is_active {
            return Err(IPError::LicenseNotFound);
        }

        // Revoke license
        license.is_active = false;
        env.storage().persistent().set(&license_key, &license);

        // Update IP tracking
        if license.license_type == LicenseType::Exclusive {
            ip.has_exclusive = false;
        } else {
            ip.active_licenses -= 1;
        }
        env.storage().persistent().set(&ip_key, &ip);

        Ok(())
    }
}

#[cfg(test)]
mod test;