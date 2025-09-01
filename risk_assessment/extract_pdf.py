import re
import nltk
from nltk.tokenize import sent_tokenize
import PyPDF2

# Ensure NLTK tokenizer is available
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

def extract_clauses(pdf_path):
    clauses = []
    buffer = ""

    # Expanded list of headings and boilerplate phrases to skip
    heading_keywords = [
        "EXHIBIT", "SCHEDULE", "ANNEXURE", "APPENDIX", "TABLE OF CONTENTS",
        "BACKGROUND", "RECITALS", "WITNESSETH", "NOW, THEREFORE", "IN WITNESS WHEREOF",
        "ARTICLE", "SECTION", "PARTIES", "PREAMBLE", "DEFINITIONS", "SIGNATURES",
        "TITLE", "INDEX", "INTRODUCTION", "COVER PAGE", "DATED", "PAGE", "CONFIDENTIAL",
        "STOCK PURCHASE AGREEMENT", "EMPLOYMENT AGREEMENT", "AGREEMENT NO", "INVITATION FOR BIDS",
        "CLAUSE", "CONTRACT DATA", "STANDARD CONTRACT CLAUSES", "GENERAL CONDITIONS",
        "NOTICE TO PROCEED", "LETTER OF ACCEPTANCE", "AGREEMENT FORM"
    ]


    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text = page.extract_text()
            if text:
                sentences = sent_tokenize(text)
                for sentence in sentences:
                    sentence_clean = sentence.strip().upper()

                    # Skip known headings or short phrases
                    if any(h in sentence_clean for h in heading_keywords):
                        continue
                    if len(sentence_clean.split()) < 5:
                        continue

                    buffer += " " + sentence.strip()
                    if re.search(r"[.;]$", sentence.strip()) and len(buffer.split()) > 20:
                        clauses.append(buffer.strip())
                        buffer = ""
        if buffer:
            clauses.append(buffer.strip())
    return clauses