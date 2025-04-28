from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def validate_answer(factor, value):
    prompt = f"""
    Please validate the following information for the real estate factor: "{factor}".
    Value: {value}

    Is it a reasonable and valid answer? Respond with 'Valid' or 'Invalid' and give a brief reason.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Validation Error: {str(e)}"
