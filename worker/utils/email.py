import requests

from utils.types import MailgunCredentials, ScheduledEmail


def send_email(
    email: ScheduledEmail,
    credentials: MailgunCredentials,
    overwrite_outgoing_emails: str | None = None,
):
    url = f"https://api.mailgun.net/v3/{credentials.MAILGUN_SENDER_DOMAIN}/messages"
    to = email.to_header
    cc = email.cc_header
    bcc = email.bcc_header

    if overwrite_outgoing_emails:
        to = [overwrite_outgoing_emails]
        cc = []
        bcc = []

    return requests.post(
        url,
        auth=("api", credentials.MAILGUN_API_KEY),
        data={
            "from": email.from_header,
            "to": to,
            "h:Reply-To": email.reply_to_header,
            "cc": cc,
            "bcc": bcc,
            "subject": email.subject,
            "html": email.body,
        },
    )
