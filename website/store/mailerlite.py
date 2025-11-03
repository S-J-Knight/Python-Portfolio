"""
MailerLite API Integration
Handles newsletter subscriber management
"""
import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class MailerLiteClient:
    """
    Simple MailerLite API client for managing subscribers
    API Docs: https://developers.mailerlite.com/docs/
    """
    
    BASE_URL = "https://connect.mailerlite.com/api"
    
    def __init__(self):
        self.api_key = settings.MAILERLITE_API_KEY
        self.group_id = settings.MAILERLITE_GROUP_ID
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def is_configured(self):
        """Check if MailerLite is properly configured"""
        return bool(self.api_key)
    
    def add_subscriber(self, email, name=None, fields=None):
        """
        Add a subscriber to MailerLite
        
        Args:
            email (str): Subscriber email address
            name (str): Subscriber name (optional)
            fields (dict): Additional custom fields (optional)
        
        Returns:
            dict: Response with 'success' key and optional 'data' or 'error'
        """
        if not self.is_configured():
            logger.warning("MailerLite API key not configured")
            return {
                'success': False,
                'error': 'MailerLite is not configured on this server'
            }
        
        data = {
            "email": email,
        }
        
        # Add name if provided
        if name:
            data["fields"] = {"name": name}
        
        # Add to specific group if configured
        if self.group_id:
            data["groups"] = [self.group_id]
        
        # Merge additional fields
        if fields:
            if "fields" not in data:
                data["fields"] = {}
            data["fields"].update(fields)
        
        try:
            response = requests.post(
                f"{self.BASE_URL}/subscribers",
                json=data,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Successfully added subscriber: {email}")
                return {
                    'success': True,
                    'data': response.json()
                }
            elif response.status_code == 409:
                # Subscriber already exists
                logger.info(f"Subscriber already exists in MailerLite: {email}")
                return {
                    'success': True,
                    'data': {"status": "exists", "email": email}
                }
            else:
                logger.error(f"MailerLite API error: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'error': f'API returned status {response.status_code}'
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"MailerLite API request failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_subscriber(self, email):
        """
        Get subscriber information by email
        
        Args:
            email (str): Subscriber email address
        
        Returns:
            dict: Subscriber data or None if not found
        """
        if not self.is_configured():
            return None
        
        try:
            response = requests.get(
                f"{self.BASE_URL}/subscribers",
                params={"filter[email]": email},
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("data"):
                    return data["data"][0]
            
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"MailerLite API request failed: {str(e)}")
            return None
    
    def update_subscriber(self, subscriber_id, fields):
        """
        Update subscriber custom fields
        
        Args:
            subscriber_id (str): MailerLite subscriber ID
            fields (dict): Fields to update
        
        Returns:
            dict: Response data or None if failed
        """
        if not self.is_configured():
            return None
        
        try:
            response = requests.put(
                f"{self.BASE_URL}/subscribers/{subscriber_id}",
                json={"fields": fields},
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully updated subscriber: {subscriber_id}")
                return response.json()
            else:
                logger.error(f"MailerLite API error: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"MailerLite API request failed: {str(e)}")
            return None
    
    def delete_subscriber(self, subscriber_id):
        """
        Delete a subscriber
        
        Args:
            subscriber_id (str): MailerLite subscriber ID
        
        Returns:
            dict: Response with 'success' key and optional 'error'
        """
        if not self.is_configured():
            return {
                'success': False,
                'error': 'MailerLite is not configured on this server'
            }
        
        try:
            response = requests.delete(
                f"{self.BASE_URL}/subscribers/{subscriber_id}",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 204:
                logger.info(f"Successfully deleted subscriber: {subscriber_id}")
                return {'success': True}
            else:
                logger.error(f"MailerLite API error: {response.status_code}")
                return {
                    'success': False,
                    'error': f'API returned status {response.status_code}'
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"MailerLite API request failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }


# Singleton instance
mailerlite_client = MailerLiteClient()
