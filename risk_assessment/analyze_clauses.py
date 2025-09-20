import json
import re
import time
from groq import Groq
from config import GROQ_API_KEY, ModelManager

groq_client = Groq(api_key=GROQ_API_KEY)
model_manager = ModelManager()

# ---------------- Safe JSON Parser ----------------
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

    # fallback if parsing fails
    return [
        {
            "Clause ID": i + start_id,
            "Contract Clause": cl,
            "Regulation": "Unknown",
            "Risk Level": "Unknown",
            "Risk Score": "0%",
            "Clause Identification": "Unknown",
            "Clause Feedback & Fix": "No feedback or recommendation available.",
            "AI-Modified Clause": "No AI-modified clause available."
        }
        for i, cl in enumerate(clauses)
    ]

# ---------------- Batch Analysis ----------------
def analyze_batch(clauses, start_id=1, retries=3, timeout=30):
    regulation_list = (
        "GDPR, UK GDPR, HIPAA, SOX, ITAR, SEC, FCPA, PCI-DSS, RBI, SEBI, IT Act, "
        "CCPA, CPRA, GLBA, FERPA, COPPA, NIST, ISO 27001, SOC 2, SOC 1, SOC 3, "
        "FINRA, MiFID II, EMIR, DORA, eIDAS, PIPEDA, LGPD, PDPA, APPI, POPIA, "
        "BDSG, Swiss FADP, CIS Controls, NYDFS, MAS TRM, Basel III, AML/KYC, "
        "OFAC, EAR, Export Control Act, Bank Secrecy Act, FedRAMP, FISMA, "
        "HITECH, CMMC, CSA STAR, IRAP, ENS, NIS2, PSD2, ePrivacy Directive, "
        "DPA 2018 (UK), PECR, PRA/FCA (UK), OSFI (Canada), HKMA, SAMA, "
        "DFSA, DIFC, QFCRA, APRA CPS 234, OAIC (Australia), Privacy Act 1988, "
        "Brazil LGPD, Mexico Federal Data Law, Chile Data Protection Bill, "
        "South Africa POPIA, Kenya Data Protection Act, Nigeria NDPR, "
        "Singapore PDPA, Malaysia PDPA, India DPDP Act 2023, China PIPL, "
        "China CSL, China DSL, Russia Federal Data Law 152-FZ, UAE PDPL, "
        "Qatar PDP Law, Bahrain PDPL, Turkey KVKK, Unknown"
    )

    prompt = f"""
You are a legal compliance analyst. Analyze the following contract clauses. 
For each clause, return ONLY valid JSON in this format:

[
  {{
    "Clause ID": 1,
    "Contract Clause": "...",
    "Regulation": "Best matching regulation(s) from: {regulation_list}",
    "Risk Level": "High/Medium/Low/Unknown",
    "Risk Score": "0-100%",
    "Clause Identification": "short explanation (max 100 words)",
    "Clause Feedback & Fix": "Combine feedback on clause clarity or risk with a recommendation to fix (max 100 words).",
    "AI-Modified Clause": "Rewrite the clause clearly, legally sound, and with reduced compliance risk. Preserve the original intent."
  }}
]

Clauses:
{json.dumps([{"Clause ID": i + start_id, "Contract Clause": cl} for i, cl in enumerate(clauses)])}
"""

    for attempt in range(retries):
        model = model_manager.get_next_model()
        try:
            response = groq_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a legal compliance analyst. Respond ONLY with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0,
                timeout=timeout
            )
            content = response.choices[0].message.content
            return safe_json_parse(content, clauses, start_id)
        except Exception as e:
            print(f"Attempt {attempt + 1} with model '{model}' failed: {type(e).__name__} → {e}")
            time.sleep(2)

    print("All retries failed. Using fallback.")
    return safe_json_parse("[]", clauses, start_id)

# ---------------- Batch Wrapper ----------------
def analyze_all_batches(clauses, start_id=1, batch_size=6, max_workers=3):
    """
    Splits clauses into batches and analyzes each batch sequentially.
    Currently max_workers is reserved for future threading/multiprocessing.
    """
    results = []
    for i in range(0, len(clauses), batch_size):
        batch = clauses[i:i + batch_size]
        batch_results = analyze_batch(batch, start_id=start_id + i)
        results.extend(batch_results)
    return results
