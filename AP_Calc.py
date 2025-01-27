import os
import logging
import requests
import pandas as pd
from settings import QBO_ACCESS_TOKEN, QBO_REALM_ID, QBO_BASE_URL
from api_qbo import refresh_access_token, update_env_file
from logging import logger


# ---------------------- QBO Fetch Logic ----------------------

def fetch_ap_aging_from_qbo():
    """
    Fetch the AP Aging Report from QuickBooks Online (QBO) API.
    """
    if not QBO_REALM_ID or not QBO_ACCESS_TOKEN:
        logger.error("QBO_REALM_ID or QBO_ACCESS_TOKEN is not set in the environment.")
        return None

    url = f"{QBO_BASE_URL}/v3/company/{QBO_REALM_ID}/reports/AgedPayableDetail"
    params = {"minorversion": "73"}
    headers = {"Authorization": f"Bearer {QBO_ACCESS_TOKEN}", "Accept": "application/json"}

    logger.info("Fetching AP Aging Report from QBO...")
    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 401:  # Handle token expiration
        logger.warning("Access token expired. Refreshing token...")
        tokens = refresh_access_token(os.getenv("QBO_REFRESH_TOKEN"))
        if tokens and "access_token" in tokens:
            new_access_token = tokens["access_token"]
            headers["Authorization"] = f"Bearer {new_access_token}"
            update_env_file("QBO_ACCESS_TOKEN", new_access_token)
            response = requests.get(url, headers=headers, params=params)
        else:
            logger.error("Failed to refresh access token.")
            return None

    if response.status_code == 200:
        logger.info("AP Aging Report fetched successfully.")
        return response.json()
    else:
        logger.error(f"Error fetching AP Aging Report: {response.status_code}, {response.text}")
        return None


# ---------------------- Data Extraction Logic ----------------------

def extract_data_to_dataframe(json_data):
    """
    Extract nested rows from JSON and convert to a DataFrame.
    """
    rows = json_data.get("Rows", {}).get("Row", [])
    data = []

    for section in rows:
        section_header = section.get("Header", {}).get("ColData", [{}])[0].get("value", "No Category")
        row_data = section.get("Rows", {}).get("Row", [])
        for row in row_data:
            if row.get("type") == "Data":
                row_values = [col.get("value", None) for col in row.get("ColData", [])]
                row_values.insert(0, section_header)  # Add section header as the first column
                data.append(row_values)

    columns = [
        "Aging Category", "Date", "Transaction Type", "Doc Num",
        "Vendor", "Due Date", "Past Due", "Amount", "Open Balance"
    ]

    return pd.DataFrame(data, columns=columns)


# ---------------------- Invoice Filtering Logic ----------------------

def filter_and_recommend(
    df, weekly_budget, exclusions, vendor_table, week_ending, already_recommended, vendor_budget_df
):
    """
    Filter and recommend invoices for payment based on prioritization and budgets.
    """
    logger.info("Starting invoice filtering and recommendation process...")

    # Normalize exclusions and Vendor column
    exclusions = [vendor.lower().strip() for vendor in exclusions]
    df["Vendor"] = df["Vendor"].str.lower().str.strip()
    logger.info(f"Exclusions applied: {exclusions}")

    # Step 1: Filter invoices
    filtered_df = df[~df["Vendor"].isin(exclusions)]
    logger.info(f"Filtered DF after exclusions: {filtered_df.shape}")

    # Filter transaction type and ensure data formatting
    filtered_df = filtered_df[filtered_df["Transaction Type"] == "Bill"]
    filtered_df["Date"] = pd.to_datetime(filtered_df["Date"], errors="coerce")
    filtered_df["Due Date"] = pd.to_datetime(filtered_df["Due Date"], errors="coerce")
    filtered_df["Past Due"] = pd.to_numeric(filtered_df["Past Due"], errors="coerce")
    filtered_df["Amount"] = pd.to_numeric(filtered_df["Amount"], errors="coerce")
    filtered_df.dropna(subset=["Amount"], inplace=True)

    # Filter by date and prioritize past due
    filtered_df = filtered_df[filtered_df["Date"] > pd.Timestamp("2024-01-01")]
    logger.info(f"Filtered DF after applying Date > 01/01/2024: {filtered_df.shape}")
    filtered_df["Is_Past_Due_45"] = filtered_df["Past Due"] >= 45

    # Merge with vendor table for priority
    vendor_table["vendor"] = vendor_table["vendor"].str.lower().str.strip()
    filtered_df = filtered_df.merge(vendor_table, left_on="Vendor", right_on="vendor", how="left")

    filtered_df["priority"] = filtered_df.get("priority", 0)  # Default priority if missing
    filtered_df.sort_values(
        by=["Is_Past_Due_45", "priority", "Due Date"],
        ascending=[False, False, True],
        inplace=True
    )
    logger.info(f"Filtered and sorted DF shape after prioritization: {filtered_df.shape}")

    # Exclude already recommended invoices
    filtered_df = filtered_df[~filtered_df["Doc Num"].isin(already_recommended)]

    # Ensure vendor and weekly budgets are numeric
    vendor_budget_df["vendor budget"] = pd.to_numeric(vendor_budget_df["vendor budget"], errors="coerce")
    weekly_budget = float(weekly_budget)

    # Fetch global vendor budget for the week ending
    global_vendor_budget = vendor_budget_df.loc[
        vendor_budget_df["week ending"] == week_ending, "vendor budget"
    ].values

    if len(global_vendor_budget) == 0:
        logger.error(f"No vendor budget found for week ending: {week_ending}")
        return pd.DataFrame(), None

    global_vendor_budget = float(global_vendor_budget[0])

    # Initialize variables for recommendations
    total_cumulative = 0.0
    recommended = []

    # Group by vendor and process invoices
    grouped = filtered_df.groupby("Vendor")
    for vendor, group in grouped:
        vendor_cumulative = 0.0

        for _, row in group.iterrows():
            invoice_amount = row["Amount"]
            remaining_vendor_budget = global_vendor_budget - vendor_cumulative
            remaining_weekly_budget = weekly_budget - total_cumulative

            # Log for debugging
            logger.debug(
                f"Processing Vendor: {vendor}, Invoice Amount: {invoice_amount}, "
                f"Remaining Vendor Budget: {remaining_vendor_budget}, "
                f"Remaining Weekly Budget: {remaining_weekly_budget}"
            )

            # Determine payment amount
            payment_amount = min(invoice_amount, remaining_vendor_budget, remaining_weekly_budget)
            if payment_amount <= 0:
                break

            vendor_cumulative += payment_amount
            total_cumulative += payment_amount

            recommended.append({
                **row.to_dict(),
                "Payment Amount": payment_amount,
                "CumulativeVendor": vendor_cumulative,
                "Cumulative": total_cumulative,
            })

            if vendor_cumulative >= global_vendor_budget or total_cumulative >= weekly_budget:
                break

    # Convert recommendations to DataFrame
    recommended_df = pd.DataFrame(recommended)
    if recommended_df.empty:
        logger.info("No invoices recommended for payment.")
        return recommended_df, None

    recommended_summary = recommended_df.groupby("Vendor").agg({
        "Doc Num": lambda x: ", ".join(x.astype(str)),
        "Payment Amount": "sum"
    }).reset_index()

    logger.info("Recommendation process complete.")
    return recommended_df, recommended_summary

# ---------------------- Save Recommendations ----------------------

def save_recommendations(recommended, output_file):
    """
    Save recommendations to an Excel file.
    """
    try:
        recommended.to_excel(output_file, index=False, engine="openpyxl")
        logger.info(f"Recommendations saved to {output_file}.")
    except Exception as e:
        logger.error(f"Error saving recommendations: {e}")


def validate_and_process_report():
    """
    Fetch and process AP Aging Report.
    """
    json_data = fetch_ap_aging_from_qbo()
    if not json_data:
        logger.error("Failed to retrieve AP Aging Report.")
        return None

    df = extract_data_to_dataframe(json_data)
    if df.empty:
        logger.warning("No valid data extracted from AP Aging Report.")
        return None

    logger.info(f"AP Aging Report processed with {len(df)} records.")
    return df
