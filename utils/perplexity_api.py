import requests
import os
from dotenv import load_dotenv
import json
import time
import re

load_dotenv()
API_KEY = os.getenv("PERPLEXITY_API_KEY")

# ---------- helpers ----------------------------------------------------------
def clean_project_name(name):
    cleaned = re.sub(r'[^\w\s]', ' ', name)
    return re.sub(r'\s+', ' ', cleaned).strip()

def fix_json_string(json_str):
    json_str = re.sub(r'([{,])\s*(\w+):', r'\1"\2":', json_str)
    json_str = json_str.replace("'", '"')
    json_str = re.sub(r'(?<!\\)"(?=(.*?".*?)*?$)', r'\"', json_str)
    return json_str

def get_required_fields():
    """Reduced column list only"""
    return [
        "Project Name",
        "Project Price per SFT",
        "total Price",
        "Possession (Year & Month)",
        "Location",
        "Builder Reputation & Legal Compliance",
        "Property Type & Space Utilization",
        "Open Space",                       # 🆕 exact open-space %
        "Safety & Security",
        "Quality of Construction",
        "Home Loan & Financing Options",
        "Orientation",
        "Configuration (2BHK, 3BHK, etc.)",
        "Source URLs",
        "Why"
    ]
# -----------------------------------------------------------------------------


def get_info_from_perplexity(project_name):
    url = "https://api.perplexity.ai/chat/completions"
    original_name = project_name
    cleaned_name = clean_project_name(project_name)

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    # 🏗️  Reduced JSON skeleton for the assistant to follow
    json_structure = '''
{
  "Project Name": "...",
  "Project Price per SFT": "...",
  "total Price": "...",
  "Possession (Year & Month)": "...",
  "Location": "...",
  "Builder Reputation & Legal Compliance": "...",
  "Property Type & Space Utilization": "...",
  "Open Space": "...",
  "Safety & Security": "...",
  "Quality of Construction": "...",
  "Home Loan & Financing Options": "...",
  "Orientation": "...",
  "Configuration (2BHK, 3BHK, etc.)": "...",
  "Source URLs": ["..."],
  "Why": "..."
  
}
'''

    prompt = f"""
You are a highly accurate real-estate data assistant.

Return detailed and structured information about the residential project “{cleaned_name}” in Telangana, India, **ONLY** for the fields in the JSON skeleton below.

**Formatting rules**
• Give direct answers.  
• **Numeric fields:** return just the number (or range) without units or extra text.  
  *Project Price per SFT*: use AssetScan and output the **range**.  
  *total Price*: give the full ticket price of the cheapest available unit.  
  *Open Space*: output the exact open-space percentage/acreage.  
• **Descriptive fields:** be concise.  
  *Home Loan & Financing Options*: list only bank names approved for loans.  
  *Why*: 1-2 short sentences on why buyers should consider the project.

**Important columns**
-In the Configuration field, check all the websites on the internet for the correct value , whichever website gives the largest number of configuration, take all those value for example 2BHK,3BHK,4BHK.I dont want this file to be left empty and check out squareyard website and take that value.

-For each configuration field,can u go through 99acres and take the size of each configuration for example 2BHK 1500sqft,3BHK 2000sqft,4BHK 2500sqft and and can u give me the size of each configuration.

For price range column give me the minimum and the highest value of the project per square feet and give me the range from the website assetscan.ai and rerait.telangana.gov.in.

and Builder Reputation & Legal Compliance- give me proper reputation and legal compliance from the website rerait.telangana.gov.in and make it more detailed and give more information

Search each field individually on:
- magicbricks.com
- squareyards.com
- assetscan.ai
- rerait.telangana.gov.in
- nobroker.in
- 99acres.com

Do **NOT** guess. Use “Information not available” where data is missing.  


Return a pure JSON object -  no markdown or back-ticks:

{json_structure}
"""

    payload = {
        "model": "sonar-pro",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4096,
        "temperature": 0.2
    }

    max_retries, retry_delay = 3, 5
    for attempt in range(max_retries):
        try:
            resp = requests.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            content = resp.json()['choices'][0]['message']['content'].strip()
            if content.startswith("```"):  # remove accidental code fences
                content = content.strip("`").strip()

            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                data = json.loads(fix_json_string(content))  # second try

            data["Project Name"] = original_name
            for key in get_required_fields():
                data.setdefault(key, "Information not available")
            return data

        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay); retry_delay *= 2
            else:
                fallback = {"Project Name": original_name,
                            "error": str(e), "Source URLs": []}
                for k in get_required_fields():
                    fallback.setdefault(k, "Information not available")
                return fallback
