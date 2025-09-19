import datetime
import os
from fastapi import FastAPI
import uvicorn, json
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from llm_loader import get_llm
from models import EmailRequest
import imaplib, email
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
load_dotenv() 

app = FastAPI()

def analyze_with_llm(email_text: str, provider=None, model=None):
    llm = get_llm(provider=provider, model=model)

    prompt = ChatPromptTemplate.from_template("""
    You are an email analysis assistant.
    Analyze the following email and select only one option:
    ---
    {email}
    ---
    Return insights in **strict JSON** format:
    {{
      "sentiment": "positive | neutral | negative",
      "urgency": "high | medium | low",
      "priority": "High | Medium | Low",
      "entities": ["list of people, companies, or dates mentioned"],
      "summary": "short 2-3 sentence summary"
    }}
    """)

    chain = prompt | llm
    result = chain.invoke({"email": email_text})

    return result

def fetch_todays_emails():
    IMAP_SERVER = "imap.gmail.com"
    EMAIL_ACCOUNT = os.getenv('EMAIL_ACCOUNT')
    APP_PASSWORD = os.getenv("APP_PASSWORD")

    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_ACCOUNT, APP_PASSWORD)
    mail.select("inbox")

    today = datetime.datetime.today()
    yesterday = (today - datetime.timedelta(days=7)).strftime("%d-%b-%Y")
    result, data = mail.search(None, f'(SINCE "{yesterday}")')

    if result != "OK":
        return []

    email_ids = data[0].split()
    emails = []

    for eid in email_ids:
        result, data = mail.fetch(eid, "(RFC822)")
        raw_email = data[0][1]
        msg = email.message_from_bytes(raw_email)

        subject = msg["subject"]
        sender = msg["from"]

        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode(errors="ignore")
                    break
        else:
            body = msg.get_payload(decode=True).decode(errors="ignore")

        emails.append({
            "id": eid.decode(),
            "subject": subject,
            "from": sender,
            "body": body.strip()
        })

    return emails

@app.post("/analyze")
async def analyze_email(data: EmailRequest):
    emails = fetch_todays_emails()
    print(emails)

    results = []
    for mail in emails:
        result = analyze_with_llm(mail["body"])

        try:
            parsed = json.loads(result)
        except json.JSONDecodeError:
            parsed = {"raw_output": result}

        results.append({
            "id": mail["id"],
            "subject": mail["subject"],
            "from": mail["from"],
            "analysis": parsed
        })

    return results

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
