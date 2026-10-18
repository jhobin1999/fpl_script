from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import smtplib
from fpl_bot import produce_message
from fpl_bot import schedule_next_run

def create_email(sender_email, receiver_email, subject, body_text):
    """
    Creates an email message with the given parameters.
    """
    # Create the message container
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = receiver_email

    # Attach the plain text body
    part1 = MIMEText(body_text, "plain")
    message.attach(part1)

    return message

def send_email(sender_email, receiver_email, app_password, smtp_server, smtp_port, message):
    """
    Sends an email using the provided SMTP server and credentials.
    """
    try:
        # Set up the SMTP server
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Upgrade the connection to secure
            server.login(sender_email, app_password)  # Log in to the server
            server.sendmail(sender_email, receiver_email, message.as_string())  # Send the email
            print("✅ Email sent successfully!")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

def main():
  """Main function to produce the email message and send it."""
  # Load credentials from GitHub Actions environment variables (or local .env)
  sender_email = os.environ.get("SENDER_EMAIL")
  receiver_email = os.environ.get("RECEIVER_EMAIL")
  app_password = os.environ.get("GMAIL_APP_PASSWORD")

  smtp_server = "smtp.gmail.com"
  smtp_port = 587

  if not all([sender_email, receiver_email, app_password]):
    print("❌ Error: Missing email credentials in environment variables.")
    return

  # Generate the email body content
  text = produce_message()

  # Create the email
  subject = "FPL Weekly Update"
  message = create_email(sender_email, receiver_email, subject, text)

  # Send the email
  send_email(
      sender_email, receiver_email, app_password, smtp_server, smtp_port, message
  )


# Run the script
if __name__ == "__main__":
  main()

  print("🏁 Script finished. Cloud runner shutting down.")