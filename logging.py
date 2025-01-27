import logging
import os

# Ensure the logs directory exists
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(f"{log_dir}/ap_aging_calculation.log"),
        logging.StreamHandler()
    ],
    force=True,
)

logger = logging.getLogger(__name__)
