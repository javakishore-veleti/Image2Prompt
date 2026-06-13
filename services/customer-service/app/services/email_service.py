"""Outbound email (password reset / verification).

Graceful, like the rest of the stack: if SMTP isn't configured the message is
logged (so the link is visible in dev) and ``sent=False`` is returned with
``success=True`` — flows never fail just because email isn't wired up.
"""

from __future__ import annotations

import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

from image2prompt_shared.dtos import BaseReq, BaseResp
from image2prompt_shared.layers import BaseService
from image2prompt_shared.observability import observe

from ..config import settings


@dataclass(kw_only=True)
class SendEmailReq(BaseReq):
    to: str
    subject: str
    body: str


@dataclass(kw_only=True)
class SendEmailResp(BaseResp):
    sent: bool = False


class EmailService(BaseService):
    def is_configured(self) -> bool:
        return bool(settings.smtp_host)

    @observe("EmailService.send")
    def send(self, req: SendEmailReq) -> SendEmailResp:
        if not self.is_configured():
            # Dev fallback: log the full body (contains the link) so it's usable.
            self.log.info("EMAIL (not configured) to=%s subject=%s\n%s", req.to, req.subject, req.body)
            return SendEmailResp(sent=False)
        try:
            msg = EmailMessage()
            msg["From"] = settings.smtp_from
            msg["To"] = req.to
            msg["Subject"] = req.subject
            msg.set_content(req.body)
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
                if settings.smtp_use_tls:
                    smtp.starttls()
                if settings.smtp_user:
                    smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.send_message(msg)
            self.log.info("email sent to=%s subject=%s", req.to, req.subject)
            return SendEmailResp(sent=True)
        except Exception as exc:  # never break the calling flow on email errors
            self.log.warning("email send failed to=%s: %s", req.to, exc)
            return SendEmailResp(success=True, sent=False, error_message=str(exc))
