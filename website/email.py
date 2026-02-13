import smtplib
import os
import time
import logging
from queue import PriorityQueue, Empty
from threading import Thread, Lock
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from flask import current_app

SMTP_HOST = "ms7.g-cloud.by"
SMTP_PORT = 465  # Или 587

EMAILS_PER_MINUTE = 10
DAILY_LIMIT = 200

PRIORITY = {
    "activation_kod": 3,
    "new_pass": 3,
    "to_admin": 1,
    "to_recipient": 1,
    "default": 0
}

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("email-service")

class Worker(Thread):
    def __init__(self, email, password, acc_id, queue):
        super().__init__(daemon=True)
        self.email = email
        self.password = password
        self.acc_id = acc_id
        self.queue = queue

        self.sent_today = 0
        self.last_sent = 0
        self.lock = Lock()

        self.start()

    def can_send(self):
        if self.sent_today >= DAILY_LIMIT:
            return False
        if time.time() - self.last_sent < 60 / EMAILS_PER_MINUTE:
            return False
        return True

    def send_email(self, to_email, subject, html):
        try:
            if SMTP_PORT == 465:
                server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=20)
            else:
                server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20)
                if SMTP_PORT == 587:
                    server.starttls()
            
            server.ehlo()
            server.login(self.email, self.password)

            msg = MIMEMultipart()
            msg["From"] = self.email
            msg["To"] = to_email
            msg["Subject"] = subject
            msg["Date"] = formatdate(localtime=True)
            msg.attach(MIMEText(html, "html"))

            server.sendmail(self.email, to_email, msg.as_string())
            server.quit()

            with self.lock:
                self.sent_today += 1
                self.last_sent = time.time()

            current_app.logger.info(f"[Account №{self.acc_id}] shipped to {to_email}")
            return True

        except Exception as e:
            current_app.logger.error(f"[Account №{self.acc_id}] Error: {str(e)}")
            return False

    def run(self):
        while True:
            try:
                pr, ts, task = self.queue.get(timeout=1)
            except Empty:
                continue

            if not self.can_send():
                time.sleep(2)
                self.queue.put((pr, ts, task))
                continue

            ok = self.send_email(
                task["to"],
                task["subject"],
                task["html"]
            )

            if not ok and task["attempt"] < 3:
                task["attempt"] += 1
                self.queue.put((pr, time.time(), task))

            self.queue.task_done()

class EmailQueue:
    def __init__(self):
        self.queue = PriorityQueue()
        self.workers = self._load_accounts()

    def _load_accounts(self):
        workers = []
        i = 1
        while True:
            email = os.getenv(f"ACC_{i}_EMAIL")
            password = os.getenv(f"ACC_{i}_PASS")
            if not email or not password:
                break

            workers.append(
                Worker(
                    email=email,
                    password=password,
                    acc_id=i,
                    queue=self.queue
                )
            )
            current_app.logger.info(f"Account #{i} ({email}) uploaded")
            i += 1

        if not workers:
            raise RuntimeError("Not a single account was found.")

        current_app.logger.info(f"Count of email accounts: {len(workers)}")
        return workers

    def add(self, to_email, subject, html, email_type="default"):
        pr = -PRIORITY.get(email_type, 0)
        self.queue.put((pr, time.time(), {
            "to": to_email,
            "subject": subject,
            "html": html,
            "attempt": 0,
            "type": email_type
        }))
        current_app.logger.info(f"The task has been added to the queue: {to_email}, type: {email_type}")

def build_html(message_body, email_type):
    if email_type == "code":
        content = f"""
        <div style='padding:20px 40px; color:#000000; font-size:15px;'>
            <p style='margin:0 0 10px 0; color:#000000;'>Здравствуйте!</p>
            <p style='margin:0 0 10px 0; color:#000000;'>Кто-то пытается войти в <b>EnergoPlans</b> используя вашу электронную почту.</p>
            <p style='margin:0 0 10px 0; color:#000000;'>Ваш код активации:</p>
            <div style='text-align:center; font-size:32px; font-weight:bold; padding:15px; margin:20px 0; color:#000000;'>{message_body}</div>
        </div>
        """
    elif email_type == "pass":
        content = f"""
        <div style='padding:20px 40px; color:#000000; font-size:15px;'>
            <p style='margin:0 0 10px 0; color:#000000;'>Здравствуйте!</p>
            <p style='margin:0 0 10px 0; color:#000000;'>Вы запросили новый пароль для входа в <b>EnergoPlans</b>.</p>
            <p style='margin:0 0 10px 0; color:#000000;'>Ваш новый пароль:</p>
            <div style='text-align:center; font-size:32px; font-weight:bold; padding:15px; margin:20px 0; color:#000000;'>{message_body}</div>
        </div>
        """
    elif email_type == "plan":
        content = f"""
        <div style='padding:20px 40px; color:#000000; font-size:15px;'>
            <p style='margin:0 0 10px 0; color:#000000;'>Здравствуйте!</p>
            <p style='margin:0 0 10px 0; color:#000000;'>Статус вашего отчета изменен на:</p>
            <div style='text-align:center; font-size:20px; font-weight:600; padding:10px; margin:15px 0; color:#000000; border:1px solid #000; border-radius:5px; display:inline-block;'>{message_body}</div>
        </div>
        """
    elif email_type == "reset_link":
        content = f"""
        <div style='padding:20px 40px; color:#000000; font-size:15px;'>
            <p style='margin:0 0 10px 0; color:#000000;'>Здравствуйте!</p>
            <p style='margin:0 0 10px 0; color:#000000;'>Вы запросили сброс пароля для вашей учетной записи в <b>EnergoPlans</b>.</p>
            <p style='margin:0 0 15px 0; color:#000000;'>Для сброса пароля перейдите по ссылке ниже:</p>
            <div style='text-align:center; margin:25px 0;'>
                <a href='{message_body}' style='background-color:#4CAF50; color:white; padding:12px 30px; text-decoration:none; border-radius:5px; font-size:16px; font-weight:bold; display:inline-block;'>
                    Сбросить пароль
                </a>
            </div>
            <p style='margin:15px 0 5px 0; color:#666; font-size:13px;'>Ссылка действительна в течение 1 часа.</p>
            <p style='margin:5px 0 0 0; color:#666; font-size:13px;'>Если вы не запрашивали сброс пароля, проигнорируйте это письмо.</p>
        </div>
        """
    else:
        content = f"<div style='padding:20px 40px; color:#000000; font-size:15px;'>{message_body}</div>"

    html_template = f"""
    <!DOCTYPE html>
    <html lang="ru">
      <body style="font-family:'Montserrat',Arial,sans-serif; background-color:#eeeeee; margin:0; padding:20px;">
        <div style="max-width:600px; margin:0 auto; background-color:#ffffff; border-radius:8px; overflow:hidden; box-shadow:0 0 6px rgba(0,0,0,0.1);">
          <div style="text-align:center; font-size:17px; font-weight:500; padding:20px 50px; color:#000000;">
            Ваша учетная запись EnergoPlans
          </div>
          {content}
          <div style="padding:10px; background-color:#eeeeee;  text-align:center; font-size:12px; color:#555555;">
            <p style="margin:5px 0;">Дополнительную информацию можно найти <a href="#" style="color:#6441a5; text-decoration:none;">здесь</a>.</p>
            <p style="margin:5px 0;">Спасибо,<br>EnergoPlans</p>
          </div>
        </div>
      </body>
    </html>
    """
    return html_template

_email_queue = None

def get_email_queue():
    global _email_queue
    if _email_queue is None:
        _email_queue = EmailQueue()
    return _email_queue

def send_email(message, recipient_email, email_type="default"):
    subject_map = {
        "code": "Код подтверждения",
        "pass": "Новый пароль",
        "reset_link": "Сброс пароля",
        "plan": "Изменения статуса плана",
        "to_recipient": "Сообщение",
        "default": "Уведомление"
    }

    html = build_html(message, email_type)
    subject = subject_map.get(email_type, "Уведомление")

    queue = get_email_queue()
    queue.add(
        to_email=recipient_email,
        subject=subject,
        html=html,
        email_type=email_type
    )
    current_app.logger.info(f"The message has been queued for {recipient_email}")
