from flask import Flask
from flask_mail import Mail, Message
import MySQLdb
import os
from dotenv import load_dotenv

# Load env vars if using .env
load_dotenv()

app = Flask(__name__)

# Same Mail config
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

mail = Mail(app)

# Connect DB
db = MySQLdb.connect(
    host="localhost",
    user=os.getenv('DB_USER'),
    passwd=os.getenv('DB_PASS'),
    db="fitness_ai"
)

cursor = db.cursor(MySQLdb.cursors.DictCursor)
cursor.execute(
    'SELECT email, name FROM users WHERE email != %s',
    [app.config['MAIL_DEFAULT_SENDER']]
)
users = cursor.fetchall()
cursor.close()

with app.app_context():
    for user in users:
        print(f"Sending to: {user['email']}")
        msg = Message(
            'Daily Progress Reminder',
            recipients=[user['email']],
            body=f"Hi {user['name']},\n\nDon’t forget to log your fitness progress today!\n\nStay healthy! 🚀"
        )
        mail.send(msg)

print("✅ All reminders sent.")
