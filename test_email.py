import os
import django
from django.core.mail import send_mail
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trimed_backend.settings')
django.setup()

def test_send_email():
    try:
        from django.conf import settings
        api_key = settings.ANYMAIL.get("SENDINBLUE_API_KEY")
        print(f"API Key Length: {len(api_key) if api_key else 'None'}")
        
        subject = 'Test Email from Trimed Backend'
        message = 'This is a test email to verify the email service configuration.'
        recipient_list = ['trimedhaiti@gmail.com']  # You can change this to your email for testing
        
        print(f"Sending email from {settings.DEFAULT_FROM_EMAIL} to {recipient_list}...")
        sent = send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            recipient_list,
            fail_silently=False,
        )
        print(f"Successfully sent {sent} email(s).")
    except Exception as e:
        print(f"Error sending email: {e}")

if __name__ == "__main__":
    test_send_email()
