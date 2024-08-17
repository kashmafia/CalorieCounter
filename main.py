import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request
from apscheduler.schedulers.background import BackgroundScheduler
from selenium import webdriver
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

email_address = os.getenv('email_address')
email_password = os.getenv('email_password')
sms_gateway = os.getenv('sms_gateway')

daily_calories_goal = None
eaten_calories = 0

# Function to send an email (which will be converted to SMS)
def send_message(to_number, body):
    msg = MIMEMultipart()
    msg['From'] = email_address
    msg['To'] = to_number
    msg['Subject'] = "Calorie Tracker"

    msg.attach(MIMEText(body, 'plain'))

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(email_address, email_password)
    text = msg.as_string()
    server.sendmail(email_address, to_number, text)
    server.quit()

# Function to prompt user to set daily calories goal
def prompt_calories_goal():
    global daily_calories_goal
    send_message(sms_gateway, "Good morning! Please reply with the amount of calories you wish to eat per day.")
    daily_calories_goal = None  # Reset daily calories goal for a new day

# Function to calculate calories from MyFitnessPal link
def calculate_calories(link):
    options = webdriver.ChromeOptions()
    options.add_argument('headless')
    driver = webdriver.Chrome(options=options)

    driver.get(link)
    page_content = driver.page_source

    driver.quit()

    soup = BeautifulSoup(page_content, 'html.parser')

    # Extract calories information
    calories_tag = soup.find('span', {'class': 'nf-kj'} if 'myfitnesspal' in link else {'class': 'nf-calc__amount'})
    if calories_tag:
        calories_text = calories_tag.get_text(strip=True)
        calories = int(calories_text.split()[0])
        return calories
    else:
        return None

# Route to handle incoming messages
@app.route('/sms', methods=['POST'])
def handle_sms():
    global daily_calories_goal, eaten_calories
    incoming_message = request.form['Body'].strip().lower()

    if daily_calories_goal is None:
        if incoming_message.isdigit():
            daily_calories_goal = int(incoming_message)
            response = f"Daily calories goal set to {daily_calories_goal} calories."
        else:
            response = "Invalid input. Please reply with a number representing your daily calories goal."
    else:
        if 'http' in incoming_message:
            calories = calculate_calories(incoming_message)
            if calories is not None:
                eaten_calories += calories
                remaining_calories = daily_calories_goal - eaten_calories
                response = f"You have {remaining_calories} calories left to eat today."
            else:
                response = "Error: Unable to calculate calories from the provided link."
        else:
            response = "Invalid input. Please reply with a valid link to a food item on MyFitnessPal.com."

    send_message(sms_gateway, response)
    return str("Message sent.")

if __name__ == '__main__':
    # Set up scheduler to send prompt
    scheduler = BackgroundScheduler()
    scheduler.add_job(prompt_calories_goal, 'cron', minute="*")

    scheduler.start()

    app.run(debug=True)
