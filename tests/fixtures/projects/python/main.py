"""Main module."""

from models import User, create_user
from services import UserService


def main():
    # Create user directly
    user1 = User("Bob")
    print(user1.greet())

    # Create user via factory
    user2 = create_user("Charlie")
    print(user2.greet())

    # Use service
    service = UserService()
    user3 = service.get_user()
    result = service.process_user(user3)
    print(result)


if __name__ == "__main__":
    main()
