import os, json, re, time
import PyPDF2, gspread
from tqdm import tqdm
from dotenv import load_dotenv
from groq import Groq
from google.oauth2.service_account import Credentials
import nltk
from nltk.tokenize import sent_tokenize

# Ensure NLTK tokenizer is available
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Google Sheets authentication
google_auth_file = "services.json"
google_sheet_scope = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file(google_auth_file, scopes=google_sheet_scope)
gs_client = gspread.authorize(creds)

gsheet_id = "1x_-QYWQ5uu50xtBHYMMasZ1jKDD1b1mLcxhmEDPWfyk"
sheet_name = "Sheet1"
try:
    worksheet = gs_client.open_by_key(gsheet_id).worksheet(sheet_name)
except gspread.exceptions.WorksheetNotFound:
    worksheet = gs_client.open_by_key(gsheet_id).add_worksheet(title=sheet_name, rows="100", cols="20")

# Semantic clause extraction
def extract_clauses(pdf_path):
    clauses = []
    buffer = ""

    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text = page.extract_text()
            if text:
                sentences = sent_tokenize(text)
                for sentence in sentences:
                    buffer += " " + sentence.strip()
                    if re.search(r"[.;]$", sentence.strip()) and len(buffer.split()) > 20:
                        clauses.append(buffer.strip())
                        buffer = ""
        if buffer:
            clauses.append(buffer.strip())
    return clauses

# Groq client
groq_client = Groq(api_key=GROQ_API_KEY)

# Safe JSON parser
def safe_json_parse(content, clauses, start_id):
    try:
        return json.loads(content)
    except:
        try:
            match = re.search(r"\[\s*{.*?}\s*\]", content, re.DOTALL)
            if match:
                return json.loads(match.group(0))
        except:
            pass
    return [
        {
            "Clause ID": i + start_id,
            "Contract Clause": cl,
            "Regulation": "Unknown",
            "Risk Level": "Unknown",
            "Risk Score": "0%",
            "AI Analysis": "Unknown"
        }
        for i, cl in enumerate(clauses)
    ]

# Analyze batch with retry and rate limit handling
def analyze_batch(clauses, start_id, retries=3, timeout=30):
    regulation_list = (
        "GDPR, HIPAA, SOX, ITAR, SEC, FCPA, PCI-DSS, RBI, SEBI, IT Act, "
        "CCPA, GLBA, FERPA, COPPA, NIST, ISO 27001, SOC 2, FINRA, MiFID II, "
        "DORA, eIDAS, UK GDPR, PIPEDA, LGPD, PDPA, APPI, POPIA, BDSG, "
        "CIS Controls, NYDFS, MAS TRM, Basel III, AML/KYC, OFAC, EAR, Unknown"
    )

    prompt = f"""
You are a legal compliance analyst. Analyze the following contract clauses. For each clause, return ONLY valid JSON in this format:
[
  {{
    "Clause ID": 1,
    "Contract Clause": "...",
    "Regulation": "{regulation_list}",
    "Risk Level": "High/Medium/Low/Unknown",
    "Risk Score": "0-100%",
    "AI Analysis": "short explanation (max 100 words)"
  }}
]

Instructions:
- Keep 'AI Analysis' concise and informative, strictly under 100 words.
- Use plain language to explain why the clause maps to a regulation and what risks it poses.
- Do not include extra commentary or formatting outside the JSON.

Clauses:
{json.dumps([{"Clause ID": i + start_id, "Contract Clause": cl} for i, cl in enumerate(clauses)])}
"""

    for attempt in range(retries):
        try:
            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are a legal compliance analyst. Respond ONLY with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0,
                timeout=timeout
            )
            content = response.choices[0].message.content
            print(f"\nBatch {start_id}-{start_id + len(clauses) - 1} succeeded.")
            print("Preview:", content[:300], "...\n")
            return safe_json_parse(content, clauses, start_id)

        except Exception as e:
            if "Rate limit reached" in str(e):
                wait_match = re.search(r"try again in (\d+)m(\d+\.\d+)s", str(e))
                if wait_match:
                    minutes = int(wait_match.group(1))
                    seconds = float(wait_match.group(2))
                    total_wait = int(minutes * 60 + seconds) + 5
                    print(f"\nRate limit hit. Waiting {total_wait} seconds before retrying...\n")
                    time.sleep(total_wait)
                    continue
            print(f"Attempt {attempt + 1} failed: {type(e).__name__} → {e}")
            time.sleep(2)

    print("All retries failed. Using fallback.")
    return safe_json_parse("[]", clauses, start_id)

# Main: PDF to Google Sheets
def process_pdf_to_sheets(pdf_path, batch_size=3):
    clauses = extract_clauses(pdf_path)
    rows = [["Clause ID", "Contract Clause", "Regulation", "Risk Level", "Risk Score", "AI Analysis"]]
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
                res["AI Analysis"]
            ])
    worksheet.clear()
    worksheet.update(values=rows, range_name="A1")

#Run
pdf = r"C:\Users\satya\OneDrive\AI_compliance_regulatory_checker\contracts\Law_Insider_americas-diamond-corp_exhibit-101-stock-purchase-agreement-stock-purchase-agreement-dated-as-of-february-11-2013-and-wi_Filed_01-03-2013_Contract.pdf"
process_pdf_to_sheets(pdf, batch_size=3)
