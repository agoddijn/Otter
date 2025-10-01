/**
 * Main module.
 */
const { User, createUser } = require('./models');
const { UserService } = require('./services');

function main() {
    // Create user directly
    const user1 = new User("Bob");
    console.log(user1.greet());
    
    // Create user via factory
    const user2 = createUser("Charlie");
    console.log(user2.greet());
    
    // Use service
    const service = new UserService();
    const user3 = service.getUser();
    const result = service.processUser(user3);
    console.log(result);
}

if (require.main === module) {
    main();
}

module.exports = { main };

