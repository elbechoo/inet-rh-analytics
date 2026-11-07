"""
Notifications - Email Sender
Envoi d'emails via Gmail SMTP
"""
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

# ============================================
# Config Gmail - à mettre dans .env
# ============================================
GMAIL_USER     = os.getenv("GMAIL_USER")      # ex: inetRH@gmail.com
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")  # App Password (16 chars)
RH_EMAIL       = os.getenv("RH_EMAIL")        # destinataire RH


def send_email(subject: str, html_body: str, to_email: str = None):
    """
    Envoyer un email HTML via Gmail SMTP
    """
    recipient = to_email or RH_EMAIL

    if not GMAIL_USER or not GMAIL_PASSWORD:
        logger.error("❌ GMAIL_USER ou GMAIL_PASSWORD manquant dans .env")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"iNET RH Intelligente <{GMAIL_USER}>"
        msg["To"]      = recipient

        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_PASSWORD)
            server.sendmail(GMAIL_USER, recipient, msg.as_string())

        logger.info(f"✅ Email envoyé à {recipient}: {subject}")
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error("❌ Authentification Gmail échouée - vérifier App Password")
        return False
    except Exception as e:
        logger.error(f"❌ Erreur envoi email: {e}")
        return False