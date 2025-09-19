# from mcp.server.models import Tool, FunctionTool
# from typing import Dict, Any
# from datetime import datetime
# import os
# from dotenv import load_dotenv

# load_dotenv()

# def analyze_emails(start_date: str, end_date: str, email: str, password: str) -> str:
#     from imap_tools import MailBox, AND
#     from dateutil import parser
#     from collections import Counter
    
#     start_dt = parser.parse(start_date)
#     end_dt = parser.parse(end_date)
    
#     with MailBox('imap.gmail.com', 993, ssl=True).login(email, password, 'INBOX') as mailbox:
#         criteria = AND(date_gte=start_dt, date_lt=end_dt)
#         emails = list(mailbox.fetch(criteria, mark_seen=False))
    
#     if not emails:
#         return "No emails found in the period."
    
#     senders = Counter(email.from_ for email in emails)
#     subjects = Counter(email.subject for email in emails)
#     lengths = [len(email.text or email.html or '') for email in emails]
    
#     summary = {
#         "total_emails": len(emails),
#         "top_senders": senders.most_common(3),
#         "top_subjects": subjects.most_common(3),
#         "average_length": sum(lengths) / len(lengths) if lengths else 0,
#     }
#     return str(summary)

# def query_document(doc_id: int, question: str) -> str:
#     from ..core.agent import DocumentAgent 
#     agent = DocumentAgent(user_id="default", doc_id=doc_id)
#     result = agent.ask(question)
#     return result['answer']  

# email_tool = FunctionTool(
#     name="analyze_emails",
#     description="Analyze emails in a time period: total count, top senders, subjects.",
#     parameters={
#         "type": "object",
#         "properties": {
#             "start_date": {"type": "string", "description": "YYYY-MM-DD"},
#             "end_date": {"type": "string", "description": "YYYY-MM-DD"},
#             "email": {"type": "string", "description": "Your email"},
#             "password": {"type": "string", "description": "App password (secure!)"},
#         },
#         "required": ["start_date", "end_date", "email", "password"]
#     },
#     function=analyze_emails
# )

# document_tool = FunctionTool(
#     name="query_document",
#     description="Query document for summary, analysis, or graph (returns text + optional base64 image).",
#     parameters={
#         "type": "object",
#         "properties": {
#             "doc_id": {"type": "integer"},
#             "question": {"type": "string", "description": "e.g., 'Summarize' or 'Make bar graph'"},
#         },
#         "required": ["doc_id", "question"]
#     },
#     function=query_document
# )

# TOOLS = [email_tool, document_tool]