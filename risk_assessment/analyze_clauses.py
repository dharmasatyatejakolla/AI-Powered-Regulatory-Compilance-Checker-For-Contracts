import os, json, re, time
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY)

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
            "Clause Identification": "Unknown",
            "Clause Feedback & Fix": "No feedback or recommendation available."
        }
        for i, cl in enumerate(clauses)
    ]

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
    "Clause Identification": "short explanation (max 100 words)",
    "Clause Feedback & Fix": "Combine feedback on clause clarity or risk with a specific recommendation to modify the clause and resolve the issue. Limit to 100 words."
  }}
]

Instructions:
- 'Clause Identification' should explain why the clause maps to a regulation and what risks it poses.
- 'Clause Feedback & Fix' must be actionable. If Risk Level is High or Medium, suggest how to rewrite, clarify, or add safeguards. Include brief feedback if the clause is vague, risky, or incomplete.
- Use plain language. No extra formatting outside the JSON.

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
            return safe_json_parse(content, clauses, start_id)

        except Exception as e:
            if "Rate limit reached" in str(e):
                wait_match = re.search(r"try again in (\d+)m(\d+\.\d+)s", str(e))
                if wait_match:
                    minutes = int(wait_match.group(1))
                    seconds = float(wait_match.group(2))
                    total_wait = int(minutes * 60 + seconds) + 5
                    print(f"\nRate limit hit. Waiting {total_wait} seconds...\n")
                    time.sleep(total_wait)
                    continue
            print(f"Attempt {attempt + 1} failed: {type(e).__name__} → {e}")
            time.sleep(2)

    print("All retries failed. Using fallback.")
    return safe_json_parse("[]", clauses, start_id)
