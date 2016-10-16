import configparser
import os
import smtplib
from os.path import basename
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate

COMMA = ", "
CONFIG_FILE = "configFile.cfg"
DEFAULT_MSG = "Enjoy!"
SERVER = "127.0.0.1"
DEFAULT_SUBJECT = "New free packt ebook"

class MailBook:

    def __init__(self):
        cfgFilePath = os.path.join(os.getcwd(), CONFIG_FILE)
        myDefaults = {'fromEmail': None,'toEmails': [],'kindleEmails': None, }
        config = configparser.ConfigParser(defaults=myDefaults)
        config.read(cfgFilePath)
        try:
            self.send_from = config.get("MAIL", 'fromEmail')
            self.to_emails = config.get("MAIL", 'toEmails').split(COMMA)
        except configparser.NoSectionError:
            raise ValueError("ERROR: need at least one from and one or more to emails")
        self.kindle_emails = config.get("MAIL", 'kindleEmails').split(COMMA)

    def send_book(self, book, to=None, subject=None, msg=None):
        if not os.path.isfile(book):
            raise
        book_name = basename(book)
        msg = MIMEMultipart()
        msg['From'] = self.send_from
        if to:
            self.to_emails = to
        msg['To'] = COMMASPACE.join(self.to_emails)
        msg['Date'] = formatdate(localtime=True)
        msg['Subject'] = subject if subject else "{}: {}".format(DEFAULT_SUBJECT, book_name)
        msg = msg if msg else DEFAULT_MSG
        msg.attach(MIMEText(msg))
        with open(book, "rb") as f:
            part = MIMEApplication(
                f.read(),
                Name=book_name
            )
            part['Content-Disposition'] = 'attachment; filename="{}"'.format(book_name)
            msg.attach(part)
        smtp = smtplib.SMTP(SERVER)
        smtp.sendmail(self.send_from, self.to_emails, msg.as_string())
        smtp.close()

    def send_kindle(self, book):
        if not self.kindle_emails:
            return
        self.send_book(book, to=self.kindle_emails) 


if __name__ == "__main__":
    mb = MailBook()
    mb.send_kindle("/home3/bobbelde/code/third-party/packt/books/Learning NGUI for Unity.mobi")
    #mb.send_mail("abc@bobcodes.it", ["hello@gmail.com"], "test", "your new free ebook for today", files=["books/somebooks.pdf"])
