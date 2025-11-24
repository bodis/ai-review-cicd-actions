"""
Test file with intentional problems for AI review validation.
This file should trigger multiple review findings.
"""

import os
import subprocess
import sqlite3

# SECURITY: Hardcoded credentials (should be caught by Bandit)
API_KEY = "sk-ant-api03-secret-key-12345"
DATABASE_PASSWORD = "admin123"
SECRET_TOKEN = "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"


def unsafe_sql_query(user_input):
    """SQL injection vulnerability - user input directly in query."""
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    # SECURITY: SQL Injection - string formatting with user input
    query = f"SELECT * FROM users WHERE username = '{user_input}'"
    cursor.execute(query)
    return cursor.fetchall()


def unsafe_command_execution(filename):
    """Command injection vulnerability."""
    # SECURITY: Command injection - unsanitized input in shell command
    result = subprocess.run(f"cat {filename}", shell=True, capture_output=True)
    return result.stdout


def unsafe_eval(user_code):
    """Arbitrary code execution vulnerability."""
    # SECURITY: eval() with user input
    return eval(user_code)


def function_with_too_many_args(a, b, c, d, e, f, g, h, i, j, k):
    """Function with too many arguments - code smell."""
    return a + b + c + d + e + f + g + h + i + j + k


def deeply_nested_function(data):
    """Deeply nested code - complexity issue."""
    if data:
        if data.get("level1"):
            if data["level1"].get("level2"):
                if data["level1"]["level2"].get("level3"):
                    if data["level1"]["level2"]["level3"].get("level4"):
                        if data["level1"]["level2"]["level3"]["level4"].get("level5"):
                            return data["level1"]["level2"]["level3"]["level4"]["level5"]
    return None


def no_type_hints(x, y):
    """Missing type hints."""
    return x + y


def unused_variable_example():
    """Unused variable - code smell."""
    used = "this is used"
    unused = "this is never used"  # noqa: F841 - intentional for testing
    return used


def bare_except_handler():
    """Bare except clause - bad practice."""
    try:
        risky_operation()
    except:  # QUALITY: Bare except catches everything including KeyboardInterrupt
        pass


def risky_operation():
    """Placeholder for risky operation."""
    raise ValueError("Something went wrong")


class InsecureClass:
    """Class with security issues."""

    def __init__(self):
        # SECURITY: Storing sensitive data in plain text
        self.password = "supersecretpassword"
        self.api_key = os.getenv("API_KEY", "default-insecure-key")

    def log_sensitive_data(self, user_data):
        """Logging sensitive information."""
        # SECURITY: Logging potentially sensitive user data
        print(f"User data: {user_data}")
        print(f"Using password: {self.password}")


def main():
    """Main function with multiple issues."""
    # Using hardcoded credentials
    api = InsecureClass()

    # SQL injection
    user_input = input("Enter username: ")
    results = unsafe_sql_query(user_input)

    # Command injection
    filename = input("Enter filename: ")
    content = unsafe_command_execution(filename)

    # Eval injection
    code = input("Enter code to execute: ")
    unsafe_eval(code)

    print(results, content)


if __name__ == "__main__":
    main()
