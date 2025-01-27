import os
import requests
import logging
import datetime
from config.logging import logger
from config.settings import SHAREPOINT_SITE_URL

# Load environment variables
SHAREPOINT_SITE_URL = os.getenv("SHAREPOINT_SITE_URL")

# Validate environment variables
if not SHAREPOINT_SITE_URL:
    logger.error("SHAREPOINT_SITE_URL is missing. Ensure settings.py is configured correctly.")
    raise ValueError("Missing required environment variables.")

def get_sharepoint_token():
    """
    Fetch the SharePoint access token from the SharePointIntegrationApp.

    Returns:
        str: Access token for SharePoint API.
    """
    try:
        response = requests.get("https://sharepointintegrationapp.azurewebsites.net/get-sharepoint-token")
        response.raise_for_status()
        return response.json().get("access_token")
    except Exception as e:
        raise Exception(f"Failed to fetch token: {e}")

def download_file_from_sharepoint(remote_path, local_path):
    """
    Download a file from SharePoint to a local directory.

    Args:
        remote_path (str): The remote path to the file on SharePoint.
        local_path (str): The local file path to save the downloaded file.
    """
    try:
        # Acquire the access token
        token = get_sharepoint_token()
        if not token:
            logger.error("Failed to acquire an access token.")
            return

        headers = {"Authorization": f"Bearer {token}"}
        url = f"{SHAREPOINT_SITE_URL}/_api/web/getfilebyserverrelativeurl('{remote_path}')/$value"

        logger.info(f"Downloading file from SharePoint: {remote_path}")
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            # Write file content to local path
            with open(local_path, 'wb') as f:
                f.write(response.content)
            logger.info(f"File downloaded successfully to: {local_path}")
        else:
            logger.error(f"Failed to download file: {response.status_code}, {response.text}")
            response.raise_for_status()
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        raise

def generate_unique_filename(filename):
    """
    Generate a unique filename by appending a timestamp.

    Args:
        filename (str): Original filename.

    Returns:
        str: Unique filename.
    """
    base, ext = os.path.splitext(filename)
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{base}_{timestamp}{ext}"

def upload_file_to_sharepoint(local_path, remote_path):
    """
    Upload a local file to SharePoint with a unique name if required.

    Args:
        local_path (str): The local file path of the file to be uploaded.
        remote_path (str): The remote path on SharePoint to save the file.
    """
    try:
        token = get_sharepoint_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/octet-stream",
        }

        # Generate a unique filename for the remote file
        unique_remote_path = generate_unique_filename(remote_path)
        folder_url = f"{SHAREPOINT_SITE_URL}/_api/web/getfolderbyserverrelativeurl('{os.path.dirname(unique_remote_path)}')"
        upload_url = f"{folder_url}/files/add(url='{os.path.basename(unique_remote_path)}',overwrite=false)"

        logger.info(f"Uploading file to SharePoint: {unique_remote_path}")
        with open(local_path, 'rb') as f:
            response = requests.post(upload_url, headers=headers, data=f)

        if response.status_code == 200:
            logger.info(f"File uploaded successfully to: {unique_remote_path}")
        else:
            logger.error(f"Failed to upload file: {response.status_code}, {response.text}")
            response.raise_for_status()
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise

if __name__ == "__main__":
    try:
        # File paths
        remote_path_download = "/sites/2023-Payables/Shared Documents/Python_Tools/AP_Aging_Payment_Calc/AP_calc_config.xlsx"
        local_path_download = "AP_calc_config.xlsx"

        remote_path_upload = "/sites/2023-Payables/Shared Documents/Python_Tools/AP_Aging_Payment_Calc/AP_calc_config_uploaded.xlsx"
        local_path_upload = "AP_calc_config.xlsx"  # Adjust as needed for your file location

        # Download the file
        logger.info("Starting file download...")
        download_file_from_sharepoint(remote_path_download, local_path_download)
        logger.info("File download completed.")

        # Upload the file
        logger.info("Starting file upload...")
        upload_file_to_sharepoint(local_path_upload, remote_path_upload)
        logger.info("File upload completed.")
    except Exception as e:
        logger.error(f"Error: {e}")
