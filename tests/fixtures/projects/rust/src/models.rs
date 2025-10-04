//! Data models.

/// User model.
pub struct User {
    pub name: String,
}

impl User {
    /// Create a new user.
    pub fn new(name: String) -> Self {
        User { name }
    }
    
    /// Greet the user.
    pub fn greet(&self) -> String {
        format!("Hello, {}!", self.name)
    }
}

/// Factory function for creating users.
pub fn create_user(name: &str) -> User {
    User::new(name.to_string())
}

/// Module constant.
pub const DEFAULT_NAME: &str = "Guest";

