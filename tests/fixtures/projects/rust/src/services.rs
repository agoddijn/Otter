//! Business logic.
use crate::models::{User, create_user};

pub struct UserService;

impl UserService {
    /// Get a user.
    pub fn get_user(&self) -> User {
        create_user("Alice")
    }
    
    /// Process a user.
    pub fn process_user(&self, user: &User) -> String {
        user.greet()
    }
}

