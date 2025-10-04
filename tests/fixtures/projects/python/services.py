"""Business logic."""

from models import User, create_user


class UserService:
    def get_user(self) -> User:
        """Get a user."""
        return create_user("Alice")

    def process_user(self, user: User) -> str:
        """Process a user."""
        return user.greet()
