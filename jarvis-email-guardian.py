#!/usr/bin/env python3
"""
Jarvis Email Guardian - Gmail Automation & Security Filter
Monitors inbox, classifies emails, responds to safe/important messages
Author: Jarvis (jarvisauto001-coder)
Repo: https://github.com/jarvisauto001-coder/moneybot-scripts

SECURITY POLICY:
- NEVER execute commands requested via email
- NEVER send sensitive data/credentials via email
- NEVER transfer funds or make payments
- NEVER click links or download attachments from unknown sources
- ALWAYS log suspicious requests as ALERTS
- PRIMARY communication channel: Telegram (this email is secondary)
"""

import os
import re
import sys
import time
import json
import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from datetime import datetime
from typing import Optional, List, Dict, Tuple

# Load credentials from .env file
def load_env_file(filepath="/root/.openclaw/workspace/.credentials/jarvis_accounts.env"):
    """Load environment variables from .env file"""
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        os.environ[key] = value

# Load credentials
load_env_file()

# Configuration
GMAIL_USER = os.getenv("JARVIS_GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.getenv("JARVIS_GMAIL_APP_PASSWORD", "")
TELEGRAM_USERNAME = "@MauricioMF"  # Primary contact

# Priority senders (whitelist of trusted contacts)
TRUSTED_SENDERS = [
    # Add trusted domains or emails here
    "jarvis.auto.001@gmail.com",  # Self
    "@clawtasks.com",  # ClawTasks platform
    "@moltbook.com",   # Moltbook platform
]

# Known spam patterns
SPAM_KEYWORDS = [
    "urgent action required", "your account will be suspended", "claim your prize",
    "you won", "lottery", "inheritance", "prince", "bitcoin investment",
    "get rich quick", "work from home", "make money fast", "loan approved",
    "verify your account now", "suspended", "locked", "click here immediately"
]

# Dangerous request patterns (NEVER comply)
DANGEROUS_PATTERNS = [
    r"run\s+(?:this\s+)?(?:command|script|code)",
    r"execute\s+(?:this|the)",
    r"send\s+(?:me\s+)?(?:your\s+)?(?:password|credential|key|token|api)",
    r"provide\s+(?:your\s+)?(?:private\s+)?(?:key|password|login)",
    r"transfer\s+(?:money|funds|btc|eth|usdc)",
    r"send\s+(?:\d+\s+)?(?:btc|eth|usdc|usd)",
    r"pay\s+(?:this|the)\s+(?:invoice|bill|amount)",
    r"click\s+(?:this\s+)?link\s+and",
    r"download\s+(?:this\s+)?attachment",
    r"install\s+(?:this\s+)?(?:software|program|app)",
    r"give\s+(?:me\s+)?access\s+to",
    r"share\s+(?:your\s+)?(?:screen|desktop|terminal)",
    r"urgent.*(?:immediately|now|asap)",
    r"(?:act|respond)\s+within\s+\d+\s*(?:hour|minute)"
]

class EmailGuardian:
    def __init__(self):
        self.log_file = "/root/.openclaw/workspace/logs/email_guardian.log"
        self.processed_ids_file = "/root/.openclaw/workspace/.email_processed_ids.json"
        self.reply_log = "/root/.openclaw/workspace/logs/email_replies.md"
        self.processed_ids = self.load_processed_ids()
        
    def log(self, level: str, message: str):
        """Log with timestamp and level"""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        print(log_entry.strip())
        
        # Ensure log directory exists
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        
        with open(self.log_file, 'a') as f:
            f.write(log_entry)
    
    def load_processed_ids(self) -> set:
        """Load previously processed email IDs"""
        if os.path.exists(self.processed_ids_file):
            try:
                with open(self.processed_ids_file, 'r') as f:
                    return set(json.load(f).get("ids", []))
            except:
                return set()
        return set()
    
    def save_processed_ids(self):
        """Save processed email IDs"""
        with open(self.processed_ids_file, 'w') as f:
            json.dump({"ids": list(self.processed_ids), "updated": datetime.utcnow().isoformat()}, f, indent=2)
    
    def connect_imap(self) -> Optional[imaplib.IMAP4_SSL]:
        """Connect to Gmail IMAP"""
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            self.log("INFO", f"Connected to Gmail IMAP as {GMAIL_USER}")
            return mail
        except Exception as e:
            self.log("ERROR", f"IMAP connection failed: {e}")
            return None
    
    def decode_email_header(self, header_value: str) -> str:
        """Decode email header safely"""
        if not header_value:
            return ""
        try:
            decoded_parts = decode_header(header_value)
            result = ""
            for part, charset in decoded_parts:
                if isinstance(part, bytes):
                    result += part.decode(charset or 'utf-8', errors='replace')
                else:
                    result += part
            return result
        except:
            return str(header_value)
    
    def extract_email_body(self, msg) -> str:
        """Extract text body from email message"""
        body = ""
        try:
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition", ""))
                    
                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        try:
                            body = part.get_payload(decode=True).decode('utf-8', errors='replace')
                            break
                        except:
                            pass
            else:
                body = msg.get_payload(decode=True).decode('utf-8', errors='replace')
        except Exception as e:
            self.log("WARN", f"Could not extract email body: {e}")
        
        return body[:5000]  # Limit body size for analysis
    
    def extract_sender_info(self, msg) -> Tuple[str, str]:
        """Extract sender name and email"""
        from_header = msg.get("From", "")
        decoded = self.decode_email_header(from_header)
        
        # Try to extract email
        email_match = re.search(r'<([^>]+)>', decoded)
        if email_match:
            sender_email = email_match.group(1).lower()
            sender_name = decoded.split('<')[0].strip()
        else:
            sender_email = decoded.lower()
            sender_name = sender_email
            
        return sender_name, sender_email
    
    def classify_email(self, sender_email: str, subject: str, body: str) -> str:
        """
        Classify email priority
        Returns: "important", "spam", "newsletter", or "low_priority"
        """
        text = (subject + " " + body).lower()
        
        # Check for spam keywords
        for keyword in SPAM_KEYWORDS:
            if keyword in text:
                return "spam"
        
        # Check if from trusted sender (PRIORITY: Always respond to my human)
        for trusted in TRUSTED_SENDERS:
            if trusted in sender_email:
                return "important"
        
        # Special case: "Teste" in subject from Gmail = likely my human testing
        if "teste" in subject.lower() and "gmail.com" in sender_email:
            return "important"
        
        # Check for newsletter patterns
        newsletter_patterns = ["unsubscribe", "newsletter", "digest", "weekly", "monthly update"]
        if any(p in text for p in newsletter_patterns):
            return "newsletter"
        
        # Check for business/opportunity keywords
        business_keywords = [
            "bounty", "proposal", "accepted", "payment", "invoice",
            "opportunity", "collaboration", "partnership", "job", "project",
            "clawtasks", "moltbook", "depin", "aioz", "agent economy"
        ]
        if any(kw in text for kw in business_keywords):
            return "important"
        
        return "low_priority"
    
    def is_dangerous_request(self, subject: str, body: str) -> Tuple[bool, str]:
        """
        Check if email contains dangerous requests
        Returns: (is_dangerous, reason)
        """
        text = (subject + " " + body).lower()
        
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                reason = f"Matched dangerous pattern: {pattern}"
                return True, reason
        
        # Check for credential requests
        credential_words = ["password", "api key", "token", "secret", "credential", "private key"]
        for word in credential_words:
            if f"send {word}" in text or f"provide {word}" in text or f"your {word}" in text:
                return True, f"Request for sensitive data ({word})"
        
        # Check for urgent action requests (common phishing)
        urgency_phrases = ["urgent", "immediate action", "act now", "expires today", "suspend"]
        urgency_count = sum(1 for phrase in urgency_phrases if phrase in text)
        if urgency_count >= 2:
            return True, "Multiple urgency triggers (likely phishing)"
        
        return False, ""
    
    def should_auto_reply(self, classification: str) -> bool:
        """Determine if we should auto-reply based on classification"""
        if classification == "spam":
            return False
        if classification == "newsletter":
            return False  # Don't reply to newsletters
        if classification == "low_priority":
            return False  # Manual review for these
        if classification == "important":
            return True
        return False
    
    def generate_reply(self, subject: str, body: str, sender_name: str) -> str:
        """Generate contextual reply for important emails"""
        text = (subject + " " + body).lower()
        
        # Detect context
        if "bounty" in text or "proposal" in text or "clawtasks" in text:
            return f"""Hi {sender_name},

Thank you for reaching out regarding this opportunity.

I've received your message and will review it carefully. For time-sensitive or critical matters, please also reach out to me via Telegram (@JarvisBot) as that's my primary communication channel for urgent items.

I'll get back to you shortly with a more detailed response.

Best regards,
Jarvis (MoneyBot)
--
⚡ Automated response - monitored 24/7"""

        if "collaboration" in text or "partnership" in text or "project" in text:
            return f"""Hi {sender_name},

Thank you for your interest in collaboration.

I'm currently managing multiple automation projects and would be happy to explore how we might work together. 

For faster coordination on active projects, please contact me via Telegram (primary channel) or expect a detailed follow-up from me within 24 hours.

Looking forward to hearing more about your proposal.

Best,
Jarvis
--
🤖 AI Assistant | MoneyBot System"""

        # Default reply for important emails
        return f"""Hi {sender_name},

Thank you for your email. I've received your message and it's been logged for review.

For urgent matters or if you need immediate assistance, please contact me via Telegram where I maintain real-time presence.

I'll respond with more details soon.

Best regards,
Jarvis
--
📧 Automated acknowledgment | Jarvis Email Guardian active"""
    
    def send_reply(self, to_email: str, to_name: str, original_subject: str, reply_body: str) -> bool:
        """Send email reply via SMTP"""
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = GMAIL_USER
            msg['To'] = to_email
            
            # Add Re: to subject if not present
            if original_subject.lower().startswith("re:"):
                msg['Subject'] = original_subject
            else:
                msg['Subject'] = f"Re: {original_subject}"
            
            msg.attach(MIMEText(reply_body, 'plain'))
            
            # Connect and send
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.send_message(msg)
            server.quit()
            
            self.log("SUCCESS", f"Reply sent to {to_email}")
            return True
            
        except Exception as e:
            self.log("ERROR", f"Failed to send reply: {e}")
            return False
    
    def save_reply_record(self, sender_email: str, subject: str, reply_sent: bool, danger_flags: str = ""):
        """Save record of reply for manual review"""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        status = "✅ REPLIED" if reply_sent else "⏸️ NO ACTION"
        
        entry = f"""### {timestamp} - {status}
- **From:** {sender_email}
- **Subject:** {subject}
- **Danger Flags:** {danger_flags if danger_flags else "None"}
- **Action:** {status}

---
"""
        
        os.makedirs(os.path.dirname(self.reply_log), exist_ok=True)
        with open(self.reply_log, 'a') as f:
            f.write(entry)
    
    def process_single_email(self, mail, email_id: bytes) -> Dict:
        """Process a single email"""
        result = {
            "id": email_id.decode(),
            "processed": False,
            "classification": None,
            "dangerous": False,
            "replied": False,
            "reason": ""
        }
        
        try:
            # Fetch email
            status, data = mail.fetch(email_id, '(RFC822)')
            if status != 'OK':
                return result
            
            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            # Extract info
            subject = self.decode_email_header(msg.get("Subject", ""))
            sender_name, sender_email = self.extract_sender_info(msg)
            body = self.extract_email_body(msg)
            
            self.log("INFO", f"Processing: [{sender_email}] {subject[:50]}...")
            
            # Classify
            classification = self.classify_email(sender_email, subject, body)
            result["classification"] = classification
            
            # Check for dangerous requests
            is_dangerous, danger_reason = self.is_dangerous_request(subject, body)
            result["dangerous"] = is_dangerous
            
            if is_dangerous:
                self.log("🚨 ALERT", f"DANGEROUS EMAIL from {sender_email}")
                self.log("🚨 ALERT", f"Reason: {danger_reason}")
                self.log("🚨 ALERT", f"Subject: {subject}")
                result["reason"] = f"DANGEROUS: {danger_reason}"
                self.save_reply_record(sender_email, subject, False, danger_reason)
                
                # Mark as processed but take no action
                self.processed_ids.add(result["id"])
                result["processed"] = True
                return result
            
            # Check if we should auto-reply
            should_reply = self.should_auto_reply(classification)
            
            if should_reply and not is_dangerous:
                # Generate and send reply
                reply_body = self.generate_reply(subject, body, sender_name)
                reply_sent = self.send_reply(sender_email, sender_name, subject, reply_body)
                result["replied"] = reply_sent
                result["reason"] = "Auto-replied to important email"
                
                if reply_sent:
                    self.log("SUCCESS", f"Auto-replied to {sender_email}")
            else:
                reason = f"Classification: {classification}"
                if not should_reply:
                    reason += " (auto-reply disabled for this class)"
                result["reason"] = reason
                self.log("INFO", f"No action: {reason}")
            
            # Save record
            self.save_reply_record(sender_email, subject, result["replied"], "")
            
            # Mark as processed
            self.processed_ids.add(result["id"])
            result["processed"] = True
            
        except Exception as e:
            self.log("ERROR", f"Error processing email {email_id}: {e}")
            result["reason"] = f"Error: {str(e)}"
        
        return result
    
    def check_inbox(self, limit: int = 10) -> List[Dict]:
        """Check inbox and process new emails"""
        results = []
        
        mail = self.connect_imap()
        if not mail:
            return results
        
        try:
            # Select inbox
            mail.select('INBOX')
            
            # Search for unread emails
            status, messages = mail.search(None, 'UNSEEN')
            if status != 'OK':
                self.log("WARN", "No messages found or search failed")
                mail.logout()
                return results
            
            email_ids = messages[0].split()
            
            if not email_ids:
                self.log("INFO", "No new unread emails")
                mail.logout()
                return results
            
            self.log("INFO", f"Found {len(email_ids)} unread emails")
            
            # Process emails (limit to avoid overload)
            for email_id in email_ids[:limit]:
                email_id_str = email_id.decode()
                
                # Skip if already processed
                if email_id_str in self.processed_ids:
                    continue
                
                result = self.process_single_email(mail, email_id)
                results.append(result)
                
                # Small delay between processing
                time.sleep(1)
            
            # Save processed IDs
            self.save_processed_ids()
            
            mail.logout()
            self.log("INFO", f"Processed {len(results)} emails")
            
        except Exception as e:
            self.log("ERROR", f"Error checking inbox: {e}")
        
        return results
    
    def generate_summary_report(self) -> str:
        """Generate summary of email activity"""
        report = f"""# 📧 Email Guardian Report
**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC

## 📊 Statistics
- **Processed IDs:** {len(self.processed_ids)}
- **Log File:** {self.log_file}
- **Reply Log:** {self.reply_log}

## 🔒 Security Rules Active
- ❌ Never execute commands from email
- ❌ Never send credentials via email  
- ❌ Never transfer funds
- ✅ Auto-reply to important emails only
- ✅ All suspicious activity logged

## 📞 Primary Contact
For urgent matters, contact via Telegram: {TELEGRAM_USERNAME}
**This email is secondary/backup channel.**

---
*Jarvis Email Guardian v1.0*
"""
        return report
    
    def run_continuous(self, interval_minutes: int = 5):
        """Run continuous monitoring loop"""
        self.log("INFO", "🚀 Email Guardian started in continuous mode")
        self.log("INFO", f"⏱️ Checking every {interval_minutes} minutes")
        self.log("INFO", f"📧 Monitoring: {GMAIL_USER}")
        
        while True:
            try:
                results = self.check_inbox(limit=10)
                
                if results:
                    stats = {
                        "important": sum(1 for r in results if r.get("classification") == "important"),
                        "spam": sum(1 for r in results if r.get("classification") == "spam"),
                        "dangerous": sum(1 for r in results if r.get("dangerous")),
                        "replied": sum(1 for r in results if r.get("replied"))
                    }
                    self.log("INFO", f"📊 Stats: Important={stats['important']}, Spam={stats['spam']}, Danger={stats['dangerous']}, Replied={stats['replied']}")
                
                # Sleep until next check
                self.log("INFO", f"⏳ Sleeping {interval_minutes} minutes...")
                time.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                self.log("INFO", "🛑 Stopped by user")
                break
            except Exception as e:
                self.log("ERROR", f"Error in main loop: {e}")
                time.sleep(60)
    
    def run_once(self):
        """Run single check"""
        self.log("INFO", "🔍 Running single inbox check...")
        results = self.check_inbox(limit=10)
        
        # Print summary
        report = self.generate_summary_report()
        print("\n" + "="*60)
        print(report)
        print("="*60)
        
        return results


def main():
    guardian = EmailGuardian()
    
    # Check command line args
    if "--once" in sys.argv:
        guardian.run_once()
    elif "--report" in sys.argv:
        print(guardian.generate_summary_report())
    else:
        guardian.run_continuous(interval_minutes=5)


if __name__ == "__main__":
    main()
