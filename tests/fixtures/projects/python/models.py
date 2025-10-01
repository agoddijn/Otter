"""Data models."""

class User:
    """User model."""
    
    def __init__(self, name: str):
        self.name = name
    
    def greet(self) -> str:
        """Greet the user."""
        return f"Hello, {self.name}!"

def create_user(name: str) -> User:
    """Factory function for creating users."""
    return User(name)

# Module constant
DEFAULT_NAME = "Guest"

