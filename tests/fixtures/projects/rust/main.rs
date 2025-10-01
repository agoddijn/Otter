//! Main module.
mod models;
mod services;

use models::{User, create_user};
use services::UserService;

fn main() {
    // Create user directly
    let user1 = User::new("Bob".to_string());
    println!("{}", user1.greet());
    
    // Create user via factory
    let user2 = create_user("Charlie");
    println!("{}", user2.greet());
    
    // Use service
    let service = UserService;
    let user3 = service.get_user();
    let result = service.process_user(&user3);
    println!("{}", result);
}

