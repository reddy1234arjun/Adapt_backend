# Import necessary modules
import smtplib
from email.mime.text import MIMEText  # MIME- Multipurpose Internet Mail Extensions
from email.mime.multipart import MIMEMultipart
from jinja2 import Environment, FileSystemLoader

def send_email(sender_email, sender_password, receiver_mail, subject, template_file, context=None):
    # Set the SMTP server and port (Outlook/Office365 in this case)
    smtp_server = 'smtp-relay.brevo.com'
    smtp_port = 587

    # Create an SMTP server object and start TLS encryption for secure communication
    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()

    try:
        # Login to the sender's email account using the provided credentials
        server.login(sender_email, sender_password)
        print("Login Success!")
    except smtplib.SMTPAuthenticationError as e:
        # If login fails, print the error message and quit the server
        print("Failed to authenticate email. Error:", str(e))
        print("Login Failed. Please check your email and password.")
        server.quit()
        exit()

    # Set up the Jinja2 environment with the current directory as the template loader
    env = Environment(loader=FileSystemLoader('.'))

    # Load the HTML template using the provided file path
    template = env.get_template(template_file)

    if context is None:
        context = {}

    # Render the template with the provided context variables
    email_content = template.render(**context)

    # Create a MIMEMultipart object for the email
    msg = MIMEMultipart()

    # Set the sender, recipient, and subject of the email
    msg['From'] = sender_email
    msg['To'] = receiver_mail
    msg['Subject'] = subject

    # Attach the HTML content to the email
    msg.attach(MIMEText(email_content, 'html'))

    try:
        # Send the email using the SMTP server
        server.sendmail(sender_email, receiver_mail, msg.as_string())
        print("Email has been sent to", receiver_mail)
    except smtplib.SMTPException as e:
        # If sending fails, print the error message
        print("Failed to send email. Error:", str(e))
        print("Sending Email Failed.")
    finally:
        # Quit the SMTP server
        server.quit()
