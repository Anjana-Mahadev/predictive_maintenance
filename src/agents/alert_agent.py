

import smtplib
import time
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class AlertAgent:
	def __init__(self, memory, smtp_server='smtp.gmail.com', smtp_port=587, smtp_user=None, smtp_pass=None, recipient='anjanamahadev79293@gmail.com'):
		self.memory = memory
		self.smtp_server = smtp_server
		self.smtp_port = smtp_port
		self.smtp_user = smtp_user or os.getenv('SMTP_USER')
		self.smtp_pass = smtp_pass or os.getenv('SMTP_PASS')
		self.recipient = recipient
		self._last_sent = 0

	def send(self, sensor_row, recs):
		now = time.time()
		# Rate limit: 5 minutes (300 seconds)
		if now - self._last_sent < 300:
			return
		subject = "[Predictive Maintenance Alert] Fault Detected"
		body = f"Fault detected!\n\nSensor Data: {sensor_row}\nRecommendations: {recs}\nTime: {time.strftime('%Y-%m-%d %H:%M:%S')}"
		msg = MIMEMultipart()
		msg['From'] = self.smtp_user or 'alert@localhost'
		msg['To'] = self.recipient
		msg['Subject'] = subject
		msg.attach(MIMEText(body, 'plain'))
		try:
			with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
				server.starttls()
				if self.smtp_user and self.smtp_pass:
					server.login(self.smtp_user, self.smtp_pass)
				server.sendmail(msg['From'], self.recipient, msg.as_string())
			self._last_sent = now
		except Exception as e:
			print(f"Failed to send alert email: {e}")
