/**
 * Business logic.
 */
const { User, createUser } = require('./models');

class UserService {
    /**
     * Get a user.
     * @returns {User}
     */
    getUser() {
        return createUser("Alice");
    }
    
    /**
     * Process a user.
     * @param {User} user
     * @returns {string}
     */
    processUser(user) {
        return user.greet();
    }
}

module.exports = { UserService };

