import gspread
from tqdm import tqdm
from google.oauth2.service_account import Credentials
from risk_assessment.analyze_clauses import analyze_batch

google_auth_file = "services.json"
google_sheet_scope = ["https://www.googleapis.com/auth/spreadsheets"]
gsheet_id = "1rPWScUeO8rCp8fjpy2d3To_Kg65qTweEV7KH5_zteB4"
sheet_name = "Sheet1"

creds = Credentials.from_service_account_file(google_auth_file, scopes=google_sheet_scope)
gs_client = gspread.authorize(creds)

try:
    worksheet = gs_client.open_by_key(gsheet_id).worksheet(sheet_name)
except gspread.exceptions.WorksheetNotFound:
    worksheet = gs_client.open_by_key(gsheet_id).add_worksheet(title=sheet_name, rows="100", cols="20")

def ingest_to_sheet(clauses, batch_size=3):
    rows = [["Clause ID", "Contract Clause", "Regulation", "Risk Level", "Risk Score", "Clause Identification"]]
    for i in tqdm(range(0, len(clauses), batch_size), desc="Processing Batches"):
        batch = clauses[i:i + batch_size]
        results = analyze_batch(batch, i + 1)
        for res in results:
            rows.append([
                res["Clause ID"],
                res["Contract Clause"],
                res["Regulation"],
                res["Risk Level"],
                res.get("Risk Score", "0%"),
                res["Clause Identification"]
            ])
    worksheet.clear()
    worksheet.update(values=rows, range_name="A1")