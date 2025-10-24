"""
Quick test script to verify MailerLite connection
Run with: python test_mailerlite.py
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'website.settings')
django.setup()

from store.mailerlite import mailerlite_client

def test_connection():
    print("Testing MailerLite connection...")
    print(f"API Key configured: {mailerlite_client.is_configured()}")
    
    if not mailerlite_client.is_configured():
        print("❌ ERROR: API key not set!")
        print("Set it with: $env:MAILERLITE_API_KEY='your-key'")
        return False
    
    print("✓ API Key is set")
    print("\nTesting API connection with a test email...")
    
    # Try to add a test subscriber
    result = mailerlite_client.add_subscriber(
        email="test@knightcycle.com",
        name="Test Subscriber"
    )
    
    if result:
        print("✅ SUCCESS! MailerLite connection is working!")
        print(f"Response: {result}")
        return True
    else:
        print("❌ ERROR: Could not connect to MailerLite")
        print("Check your API key and internet connection")
        return False

if __name__ == "__main__":
    test_connection()
