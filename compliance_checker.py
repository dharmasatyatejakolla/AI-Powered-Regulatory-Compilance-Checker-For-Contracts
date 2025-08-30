from groq import Groq
import pygsheets
import os
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")


gc = pygsheets.authorize(service_file="service_account.json")

sh = gc.open_by_url(
    "https://docs.google.com/spreadsheets/d/1U4NNhjlMdfN0rhgANzsroBCvBJgtCX3rr8_RKQt06KQ/edit?gid=0#gid=0"
)
wks = sh.sheet1


client = Groq(api_key=api_key)


rows = wks.get_all_records()

for i, row in enumerate(rows, start=2):  
    clause = row["Contract Clause"]
    regulation = row["Regulation"]

    if not clause:  
        continue

    prompt = (
        f"Analyze this contract clause for {regulation} compliance. "
        f"Return the result in this format ONLY:\n"
        f"Summary: <your 1-2 sentence summary under 100 words>\n"
        f"Risk: <High/Medium/Low>\n\n"
        f"Clause: {clause}"
    )

    chat = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150,
    )

    result = chat.choices[0].message.content.strip()

   
    summary = ""
    risk_level = "Unknown"

    for line in result.splitlines():
        if line.startswith("Summary:"):
            summary = line.replace("Summary:", "").strip()
        elif line.startswith("Risk:"):
            risk_text = line.replace("Risk:", "").strip()
            if "High" in risk_text:
                risk_level = "High"
            elif "Medium" in risk_text:
                risk_level = "Medium"
            elif "Low" in risk_text:
                risk_level = "Low"

   
    wks.update_value(f"E{i}", summary)     
    wks.update_value(f"D{i}", risk_level)  
print("✅ All clauses analyzed by Groq and updated in Google Sheets!")
