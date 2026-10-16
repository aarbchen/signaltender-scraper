import os
from dotenv import load_dotenv
from pyairtable import Api

# Load environment variables
load_dotenv(dotenv_path=r"D:\Daas\.env")
AIRTABLE_API_KEY = os.getenv("AIRTABLE_PAT")
BASE_ID = "appRtnHZ9HeDcr0hu"
TABLE_NAME = "Contracts"

def clear_table():
    print("[*] Connecting to Airtable...")
    api = Api(AIRTABLE_API_KEY)
    table = api.table(BASE_ID, TABLE_NAME)
    
    print("[*] Fetching all records...")
    records = table.all()
    
    if not records:
        print("[+] Table is already empty.")
        return

    print(f"[*] Found {len(records)} records. Deleting...")
    
    # Extract record IDs
    record_ids = [rec['id'] for rec in records]
    
    # pyairtable automatically handles the 10-record-per-batch API limit during batch_delete
    table.batch_delete(record_ids)
    
    print(f"[+] Successfully deleted {len(records)} bids. The database is clean.")

if __name__ == "__main__":
    clear_table()