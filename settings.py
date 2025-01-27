from dotenv import load_dotenv
load_dotenv()
import os

# QuickBooks API Configuration
QBO_CLIENT_ID = os.getenv("QBO_CLIENT_ID")
QBO_CLIENT_SECRET = os.getenv("QBO_CLIENT_SECRET")
QBO_REDIRECT_URI = os.getenv("QBO_REDIRECT_URI", "https://your-production-redirect-uri.com")
QBO_BASE_URL = os.getenv("QBO_BASE_URL", "https://quickbooks.api.intuit.com")
QBO_AUTH_URL = os.getenv("QBO_AUTH_URL", "https://appcenter.intuit.com/connect/oauth2")
QBO_TOKEN_URL = os.getenv("QBO_TOKEN_URL", "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer")
QBO_REALM_ID = os.getenv("QBO_REALM_ID")
QBO_ACCESS_TOKEN = os.getenv("QBO_ACCESS_TOKEN")
QBO_REFRESH_TOKEN = os.getenv("QBO_REFRESH_TOKEN")

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///qbo_data.db")

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Pagination Defaults
DEFAULT_PAGE_SIZE = int(os.getenv("DEFAULT_PAGE_SIZE", 100))

# SharePoint API Configuration
SHAREPOINT_SITE_URL = os.getenv("SHAREPOINT_SITE_URL")
SHAREPOINT_CLIENT_ID = os.getenv("SHAREPOINT_CLIENT_ID")
SHAREPOINT_TENANT_ID = os.getenv("SHAREPOINT_TENANT_ID")
SHAREPOINT_CLIENT_SECRET = os.getenv("SHAREPOINT_CLIENT_SECRET")
SHAREPOINT_FOLDER_PATH = os.getenv("SHAREPOINT_FOLDER_PATH")
SHAREPOINT_REMOTE_INPUT_FILE = os.getenv("SHAREPOINT_REMOTE_INPUT_FILE")
SHAREPOINT_REMOTE_OUTPUT_FILE = os.getenv("SHAREPOINT_REMOTE_OUTPUT_FILE")

# Local File Paths
LOCAL_INPUT_FILE = os.getenv("LOCAL_INPUT_FILE", "Inputs/AP_calc_config.xlsx")
LOCAL_OUTPUT_FILE = os.getenv("LOCAL_OUTPUT_FILE", "Outputs/recommended_payments_monthly.xlsx")
