/**
 * Data models.
 */

class User {
    /**
     * User model.
     * @param {string} name
     */
    constructor(name) {
        this.name = name;
    }
    
    /**
     * Greet the user.
     * @returns {string}
     */
    greet() {
        return `Hello, ${this.name}!`;
    }
}

/**
 * Factory function for creating users.
 * @param {string} name
 * @returns {User}
 */
function createUser(name) {
    return new User(name);
}

// Module constant
const DEFAULT_NAME = "Guest";

module.exports = { User, createUser, DEFAULT_NAME };

