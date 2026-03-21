"""
Email Agent Tool – IMAP & SMTP Integration

Provides email capabilities including:
- Get last N emails from inbox
- Send emails
- Get email summaries
- Delete emails
- Mark emails as read/unread

Uses IMAP for retrieval and SMTP for sending.
Requires 'google_app_pwd' connector (JSON format) with:
  {
    "email": "user@gmail.com",
    "password": "app-specific-password",
    "imap_server": "imap.gmail.com",
    "smtp_server": "smtp.gmail.com"
  }
"""

import os
import json
from typing import Any, Dict, List, Optional
from datetime import datetime
from dotenv import load_dotenv
import imaplib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

try:
    from pylibs.connector import ConnectorManager
except Exception:
    ConnectorManager = None

load_dotenv()


# Email configuration defaults for Gmail
DEFAULT_IMAP_SERVER = "imap.gmail.com"
DEFAULT_SMTP_SERVER = "smtp.gmail.com"
DEFAULT_IMAP_PORT = 993
DEFAULT_SMTP_PORT = 587


class EmailClient:
    """IMAP/SMTP Email Client"""
    
    def __init__(self, email: str, password: str, 
                 imap_server: str = DEFAULT_IMAP_SERVER,
                 smtp_server: str = DEFAULT_SMTP_SERVER):
        """Initialize email client with credentials"""
        self.email = email
        self.password = password
        self.imap_server = imap_server
        self.smtp_server = smtp_server
        self.imap_conn = None
        self.smtp_conn = None
    
    def _connect_imap(self) -> bool:
        """Connect to IMAP server"""
        try:
            self.imap_conn = imaplib.IMAP4_SSL(self.imap_server, DEFAULT_IMAP_PORT)
            self.imap_conn.login(self.email, self.password)
            return True
        except Exception as e:
            raise Exception(f"IMAP connection failed: {str(e)}")
    
    def _connect_smtp(self) -> bool:
        """Connect to SMTP server"""
        try:
            self.smtp_conn = smtplib.SMTP(self.smtp_server, DEFAULT_SMTP_PORT)
            self.smtp_conn.starttls()
            self.smtp_conn.login(self.email, self.password)
            return True
        except Exception as e:
            raise Exception(f"SMTP connection failed: {str(e)}")
    
    def disconnect_imap(self):
        """Close IMAP connection"""
        if self.imap_conn:
            try:
                self.imap_conn.close()
                self.imap_conn.logout()
            except:
                pass
    
    def disconnect_smtp(self):
        """Close SMTP connection"""
        if self.smtp_conn:
            try:
                self.smtp_conn.quit()
            except:
                pass
    
    def get_last_emails(self, num_emails: int = 10, folder: str = "INBOX") -> List[Dict[str, Any]]:
        """Get last N emails from specified folder"""
        try:
            self._connect_imap()
            self.imap_conn.select(folder)
            
            # Search for all emails
            status, messages = self.imap_conn.search(None, "ALL")
            email_ids = messages[0].split()
            
            # Get last N emails
            email_ids = email_ids[-num_emails:][::-1]  # Reverse to get newest first
            
            emails = []
            for email_id in email_ids:
                status, msg_data = self.imap_conn.fetch(email_id, "(RFC822)")
                try:
                    from email import message_from_bytes
                    msg = message_from_bytes(msg_data[0][1])
                    
                    email_info = {
                        "id": email_id.decode() if isinstance(email_id, bytes) else email_id,
                        "from": msg.get("From", "Unknown"),
                        "to": msg.get("To", ""),
                        "subject": msg.get("Subject", "(No Subject)"),
                        "date": msg.get("Date", ""),
                        "body": self._get_email_body(msg),
                    }
                    emails.append(email_info)
                except Exception as e:
                    continue
            
            self.disconnect_imap()
            return emails
        
        except Exception as e:
            self.disconnect_imap()
            raise Exception(f"Failed to get emails: {str(e)}")
    
    def _get_email_body(self, msg) -> str:
        """Extract plain text body from email message"""
        body = ""
        try:
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break
                    elif part.get_content_type() == "text/html":
                        # Fallback to HTML if no plain text
                        if not body:
                            body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
            else:
                body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
        except:
            body = msg.get_payload()
        
        return body[:500] if body else "(No message body)"  # Limit to 500 chars
    
    def send_email(self, to: str, subject: str, body: str, 
                   cc: Optional[str] = None, bcc: Optional[str] = None) -> Dict[str, Any]:
        """Send an email"""
        try:
            self._connect_smtp()
            
            msg = MIMEMultipart("alternative")
            msg["From"] = self.email
            msg["To"] = to
            msg["Subject"] = subject
            
            if cc:
                msg["Cc"] = cc
            
            # Attach plain text and HTML versions
            part1 = MIMEText(body, "plain")
            msg.attach(part1)
            
            # Send email
            recipients = [to]
            if cc:
                recipients.extend(cc.split(","))
            if bcc:
                recipients.extend(bcc.split(","))
            
            self.smtp_conn.sendmail(self.email, recipients, msg.as_string())
            self.disconnect_smtp()
            
            return {
                "status": "success",
                "message": f"Email sent to {to}",
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            self.disconnect_smtp()
            return {
                "status": "error",
                "message": f"Failed to send email: {str(e)}"
            }
    
    def delete_email(self, email_id: str, folder: str = "INBOX") -> Dict[str, Any]:
        """Delete an email"""
        try:
            self._connect_imap()
            self.imap_conn.select(folder)
            self.imap_conn.store(email_id, "+FLAGS", "\\Deleted")
            self.imap_conn.expunge()
            self.disconnect_imap()
            
            return {
                "status": "success",
                "message": f"Email {email_id} deleted"
            }
        
        except Exception as e:
            self.disconnect_imap()
            return {
                "status": "error",
                "message": f"Failed to delete email: {str(e)}"
            }
    
    def mark_as_read(self, email_id: str, folder: str = "INBOX") -> Dict[str, Any]:
        """Mark email as read"""
        try:
            self._connect_imap()
            self.imap_conn.select(folder)
            self.imap_conn.store(email_id, "+FLAGS", "\\Seen")
            self.disconnect_imap()
            
            return {
                "status": "success",
                "message": f"Email {email_id} marked as read"
            }
        
        except Exception as e:
            self.disconnect_imap()
            return {
                "status": "error",
                "message": f"Failed to mark email: {str(e)}"
            }


def get_connector_credentials() -> Dict[str, str]:
    """
    Get credentials from the 'google_app_pwd' connector JSON.
    
    The connector is stored in environment variable google_app_pwd as JSON:
    {
        "email": "your-email@gmail.com",
        "password": "your-app-password",
        "imap_server": "imap.gmail.com",
        "smtp_server": "smtp.gmail.com"
    }
    
    Returns:
        Dict with email, password, imap_server, smtp_server
    
    Raises:
        Exception if connector not found or invalid
    """
    def _validate_connector_config(config: Dict[str, Any]) -> Dict[str, str]:
        required_fields = ["email", "password", "imap_server", "smtp_server"]
        for field in required_fields:
            if not config.get(field):
                raise ValueError(f"Missing required field in connector config: {field}")
        return {
            "email": str(config["email"]),
            "password": str(config["password"]),
            "imap_server": str(config["imap_server"]),
            "smtp_server": str(config["smtp_server"]),
        }

    db_error = None

    if ConnectorManager is not None:
        try:
            manager = ConnectorManager()
            connector = manager.get_connector("google_app_pwd")
            if connector and (connector.get("status") == "ACTIVE"):
                config = connector.get("config") or {}
                return _validate_connector_config(config)
        except Exception as exc:
            db_error = str(exc)

    try:
        connector_json = os.getenv("GOOGLE_APP_PWD")

        if not connector_json:
            raise ValueError(
                "Connector 'google_app_pwd' not found in DB and GOOGLE_APP_PWD env is not set. "
                "Expected connector config JSON with keys: email, password, imap_server, smtp_server"
            )

        config = json.loads(connector_json)
        return _validate_connector_config(config)

    except json.JSONDecodeError as e:
        raise Exception(f"Invalid JSON in GOOGLE_APP_PWD connector: {str(e)}")
    except Exception as e:
        if db_error:
            raise Exception(f"Failed to get connector credentials (DB error: {db_error}; ENV fallback error: {str(e)})")
        raise Exception(f"Failed to get connector credentials: {str(e)}")


def email_agent_imps(
    action: str,
    email: Optional[str] = None,
    password: Optional[str] = None,
    imap_server: Optional[str] = None,
    smtp_server: Optional[str] = None,
    num_emails: int = 10,
    to: Optional[str] = None,
    subject: Optional[str] = None,
    body: Optional[str] = None,
    email_id: Optional[str] = None,
    folder: str = "INBOX",
    cc: Optional[str] = None,
    bcc: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Email Agent Tool with IMAP & SMTP support.
    
    Uses the 'google_app_pwd' connector stored as JSON in environment variable.
    
    Actions:
    - get_last_emails:     Retrieve last N emails from inbox
    - send_email:          Send an email
    - delete_email:        Delete an email by ID
    - mark_as_read:        Mark email as read
    - get_email_summary:   Get summary/preview of emails
    
    Args:
        action (str): The action to perform (required)
        email (str): Email address (optional, overrides connector if provided)
        password (str): Email password (optional, overrides connector if provided)
        imap_server (str): IMAP server (optional, overrides connector if provided)
        smtp_server (str): SMTP server (optional, overrides connector if provided)
        num_emails (int): Number of emails to retrieve (default: 10)
        to (str): Recipient email address (required for send_email)
        subject (str): Email subject (required for send_email)
        body (str): Email body text (required for send_email)
        email_id (str): Email ID (required for delete_email and mark_as_read)
        folder (str): Email folder to operate on (default: 'INBOX')
        cc (str): CC recipients, comma-separated (optional for send_email)
        bcc (str): BCC recipients, comma-separated (optional for send_email)
    
    Returns:
        Dict with:
        - status: "success" or "error"
        - action: The action performed
        - Additional fields based on action (emails, message, summary, etc.)
    
    Example Usage:
        # Get last 10 emails using google_app_pwd connector
        result = email_agent_imps(
            action="get_last_emails",
            num_emails=10
        )
        
        # Send email using connector credentials
        result = email_agent_imps(
            action="send_email",
            to="recipient@example.com",
            subject="Hello",
            body="This is my message"
        )
        
        # Override connector with explicit credentials
        result = email_agent_imps(
            action="get_last_emails",
            email="user@gmail.com",
            password="app-specific-password",
            imap_server="imap.gmail.com",
            smtp_server="smtp.gmail.com",
            num_emails=5
        )
    """
    
    try:
        # Get credentials from google_app_pwd connector
        if not email or not password or not imap_server or not smtp_server:
            creds = get_connector_credentials()
            email = email or creds["email"]
            password = password or creds["password"]
            imap_server = imap_server or creds["imap_server"]
            smtp_server = smtp_server or creds["smtp_server"]
        
        client = EmailClient(email, password, imap_server, smtp_server)
        
        # Route actions
        if action == "get_last_emails":
            emails = client.get_last_emails(num_emails=num_emails, folder=folder)
            return {
                "status": "success",
                "action": "get_last_emails",
                "count": len(emails),
                "emails": emails
            }
        
        elif action == "send_email":
            if not to or not subject or not body:
                return {
                    "status": "error",
                    "message": "Missing required fields: to, subject, body"
                }
            result = client.send_email(to, subject, body, cc, bcc)
            return result
        
        elif action == "delete_email":
            if not email_id:
                return {
                    "status": "error",
                    "message": "Missing required field: email_id"
                }
            result = client.delete_email(email_id, folder)
            return result
        
        elif action == "mark_as_read":
            if not email_id:
                return {
                    "status": "error",
                    "message": "Missing required field: email_id"
                }
            result = client.mark_as_read(email_id, folder)
            return result
        
        elif action == "get_email_summary":
            emails = client.get_last_emails(num_emails=num_emails, folder=folder)
            summary = {
                "status": "success",
                "action": "get_email_summary",
                "total_emails": len(emails),
                "emails_summary": []
            }
            
            for email_info in emails:
                summary["emails_summary"].append({
                    "from": email_info["from"],
                    "subject": email_info["subject"],
                    "date": email_info["date"],
                    "preview": email_info["body"][:200] + "..." if len(email_info["body"]) > 200 else email_info["body"]
                })
            
            return summary
        
        else:
            return {
                "status": "error",
                "message": f"Unknown action: {action}. Valid actions: get_last_emails, send_email, delete_email, mark_as_read, get_email_summary"
            }
    
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "action": action
        }
