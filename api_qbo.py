import os
import requests
from config.settings import (
    QBO_CLIENT_ID,
    QBO_CLIENT_SECRET,
    QBO_TOKEN_URL,
    QBO_REFRESH_TOKEN
)
from config.logging import logger  # Import shared logger

def refresh_access_token(refresh_token):
    """
    Refresh the Access Token using the Refresh Token and update the .env file automatically.
    """
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }

    auth = (QBO_CLIENT_ID, QBO_CLIENT_SECRET)

    logger.info("Refreshing access token...")
    response = requests.post(QBO_TOKEN_URL, data=data, auth=auth)

    if response.status_code == 200:
        tokens = response.json()
        new_access_token = tokens.get("access_token")
        new_refresh_token = tokens.get("refresh_token")

        # Update .env file
        update_env_file("QBO_ACCESS_TOKEN", new_access_token)
        update_env_file("QBO_REFRESH_TOKEN", new_refresh_token)

        logger.info("Access token refreshed successfully.")
        return tokens  # Return the parsed JSON response
    else:
        error_message = response.text  # Log the raw response content for debugging
        logger.error(f"Error refreshing token: {error_message}")
        return None

def update_env_file(key, value):
    """
    Update a key-value pair in the .env file located in the 'config' folder.
    Create the file if it doesn't exist.
    """
    env_path = os.path.join("config", ".env")
    
    try:
        # Read the .env file
        with open(env_path, "r") as file:
            lines = file.readlines()
    except FileNotFoundError:
        # If file doesn't exist, start with an empty list
        lines = []

    # Update or add the key-value pair
    updated = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}\n"
            updated = True
            break

    if not updated:
        # Append new key-value pair if not found
        lines.append(f"{key}={value}\n")

    # Write back to the .env file
    with open(env_path, "w") as file:
        file.writelines(lines)

    logger.info(f"Updated {key} in .env file.")

if __name__ == "__main__":
    logger.info("Running api_utils.py as a standalone script.")

    # Call the refresh_access_token function for testing
    tokens = refresh_access_token(QBO_REFRESH_TOKEN)
    if tokens:
        logger.info("Tokens refreshed successfully.")
    else:
        logger.error("Failed to refresh tokens.")
