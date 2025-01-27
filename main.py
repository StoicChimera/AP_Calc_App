import logging
import os
import pandas as pd
from utils.api_share import download_file_from_sharepoint, upload_file_to_sharepoint
from AP_Calc import validate_and_process_report, filter_and_recommend, save_recommendations
from config.logging import logger

# File paths
REMOTE_INPUT_FILE = os.getenv("SHAREPOINT_REMOTE_INPUT_FILE")
LOCAL_INPUT_FILE = "Inputs/AP_calc_config.xlsx"
REMOTE_OUTPUT_FILE = os.getenv("SHAREPOINT_REMOTE_OUTPUT_FILE")
LOCAL_OUTPUT_FILE = "Outputs/recommended_payments_monthly.xlsx"

def validate_config_file(config_data):
    """
    Validate the structure of the configuration file.
    """
    required_sheets = {"Config", "Vendors"}
    if not required_sheets.issubset(set(config_data.keys())):
        missing_sheets = required_sheets - set(config_data.keys())
        raise ValueError(f"Missing required sheets in the input file: {missing_sheets}")

if __name__ == "__main__":
    logger.info("Starting AP Aging Calculation Process...")

    try:
        # Step 1: Download the input file from SharePoint
        logger.info(f"Downloading input file from SharePoint: {REMOTE_INPUT_FILE}")
        download_file_from_sharepoint(REMOTE_INPUT_FILE, LOCAL_INPUT_FILE)
        logger.info("Input file downloaded successfully.")

        # Step 2: Validate and process the AP Aging Report
        logger.info("Validating and processing the AP Aging Report...")
        df = validate_and_process_report()

        if df is not None:
            try:
                # Step 3: Load and validate configuration
                logger.info("Loading configuration from input file...")
                config_data = pd.read_excel(LOCAL_INPUT_FILE, sheet_name=None, engine="openpyxl")
                validate_config_file(config_data)

                # Extract Config and Vendors sheets
                budget = config_data["Config"]
                vendor_table = config_data["Vendors"]

                # Normalize column names and 'config type'
                budget.columns = budget.columns.str.strip().str.lower()
                vendor_table.columns = vendor_table.columns.str.strip().str.lower()
                budget["config type"] = budget["config type"].str.strip().str.lower()

                # Debug column names and data
                logger.info(f"Config sheet columns: {list(budget.columns)}")
                logger.info(f"Vendors sheet columns: {list(vendor_table.columns)}")

                # Extract exclusions
                exclusions_list = budget[
                    (budget["config type"] == "exclusion") &
                    (budget["vendor name"].notna())
                ]["vendor name"].str.lower().tolist()
                logger.info(f"Exclusions List: {exclusions_list}")

                # Filter weekly budget rows
                weekly_budget_df = budget[
                    (budget["config type"] == "budget") &
                    (budget["weekly budget"].notna())
                ][["week ending", "weekly budget"]]
                logger.info(f"Weekly Budget DataFrame:\n{weekly_budget_df}")

                # Define global vendor budget
                vendor_budget_df = budget[
                    (budget["config type"] == "budget") &
                    (budget["vendor budget"].notna())
                ][["week ending", "vendor budget"]]
                logger.info(f"Global Vendor Budget DataFrame:\n{vendor_budget_df}")

                # Track already recommended invoices
                already_recommended = set()

                # Process recommendations for each week ending in the weekly budget DataFrame
                all_recommendations = pd.DataFrame()
                for _, row in weekly_budget_df.iterrows():
                    week_ending = row["week ending"]
                    weekly_budget = row["weekly budget"]

                    # Skip invalid rows
                    if pd.isna(week_ending) or pd.isna(weekly_budget):
                        logger.warning("Skipping invalid budget entry.")
                        continue

                    logger.info(f"Processing recommendations for week ending: {week_ending}...")
                    recommended, summary = filter_and_recommend(
                        df, weekly_budget, exclusions_list, vendor_table, week_ending, already_recommended, vendor_budget_df
                    )
                    if not recommended.empty:
                        # Add recommended invoices to the already recommended set
                        already_recommended.update(recommended["Doc Num"].tolist())

                        recommended["Week Ending"] = week_ending
                        all_recommendations = pd.concat([all_recommendations, recommended], ignore_index=True)

                # Step 4: Save recommendations locally
                if not all_recommendations.empty:
                    save_recommendations(all_recommendations, LOCAL_OUTPUT_FILE)
                    logger.info(f"Recommendations saved locally: {LOCAL_OUTPUT_FILE}")

                    # Step 5: Upload the output file to SharePoint
                    logger.info(f"Uploading output file to SharePoint: {REMOTE_OUTPUT_FILE}")
                    upload_file_to_sharepoint(LOCAL_OUTPUT_FILE, REMOTE_OUTPUT_FILE)
                    logger.info(f"Recommendations uploaded to SharePoint: {REMOTE_OUTPUT_FILE}")
                else:
                    logger.info("No recommendations to save.")

            except Exception as e:
                logger.error(f"Error processing data: {e}", exc_info=True)
        else:
            logger.error("Failed to process AP Aging Report.")
    except Exception as main_exception:
        logger.error(f"An error occurred during the AP Aging Calculation Process: {main_exception}", exc_info=True)

    logger.info("AP Aging Calculation Process Complete.")
