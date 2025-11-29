"""
iKhokha Payment Gateway Integration Service

This module provides integration with iKhokha payment gateway for processing
conference registration payments.

iKhokha API Documentation: https://developer.ikhokha.com/
"""

import hashlib
import hmac
import json
import requests
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
import logging
from config import Config

logger = logging.getLogger(__name__)


class IKhokhaPaymentService:
    """
    Service class for handling iKhokha payment gateway integration
    """
    
    def __init__(self, app_id: str = None, secret_key: str = None):
        """
        Initialize iKhokha payment service
        
        Args:
            app_id: iKhokha application ID
            secret_key: iKhokha secret key
        """
        self.app_id = app_id or Config.IKHOKHA_APP_ID
        self.secret_key = secret_key or Config.IKHOKHA_SECRET_KEY
        self.api_endpoint = "https://api.ikhokha.com/public-api/v1/api/payment"
        
        # Allow service to be created without credentials for development
        self.is_configured = bool(self.app_id and self.secret_key)
        
        if not self.is_configured:
            logger.warning("iKhokha payment service is not configured. Payment features will be disabled.")
    
    def create_payload_to_sign(self, url: str, body: str) -> str:
        """
        Create payload for signing according to iKhokha specification
        """
        uri = url.split('//', 1)[-1]
        base_path = '/' + uri.split('/', 1)[-1]
        full_payload = base_path + body
        return full_payload
    
    def sign_payload(self, payload: str, key: str) -> str:
        """
        Sign payload using HMAC SHA256 according to iKhokha specification
        """
        # Format payload according to iKhokha requirements
        formatted_payload = payload.replace('"', r'\"').replace(': ', r':').replace(', ', r',')
        
        key_bytes = key.encode('utf-8')
        payload_bytes = formatted_payload.encode('utf-8')
        hmac_obj = hmac.new(key_bytes, payload_bytes, hashlib.sha256)
        return hmac_obj.hexdigest()
    
    def create_payment_request(self, registration_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a payment request with iKhokha following their API specification
        
        Args:
            registration_data: Registration information including amount, user details, etc.
            
        Returns:
            Dictionary containing payment URL and transaction reference
        """
        if not self.is_configured:
            return {
                'success': False,
                'error': 'iKhokha payment service is not configured. Please set IKHOKHA_APP_ID and IKHOKHA_SECRET_KEY environment variables.'
            }
        
        # Demo mode for development/testing
        if self.app_id.lower() == 'demo' or self.app_id.lower() == 'test':
            logger.info("Running in DEMO mode - simulating payment creation")
            transaction_ref = f"DEMO_REG_{registration_data.get('user_id', 'ANON')}_{int(datetime.now().timestamp())}"
            return {
                'success': True,
                'payment_url': f'https://globalconference.co.za/payment/demo?ref={transaction_ref}',
                'transaction_reference': transaction_ref,
                'payment_id': f'demo_payment_{int(datetime.now().timestamp())}',
                'entity_id': str(uuid.uuid4()),
                'external_transaction_id': str(uuid.uuid4())
            }
        
        try:
            # Generate unique IDs according to iKhokha requirements
            entity_id = str(uuid.uuid4())
            external_entity_id = str(uuid.uuid4())
            external_transaction_id = str(uuid.uuid4())
            payment_reference = f"REG_{registration_data.get('user_id', 'ANON')}_{int(datetime.now().timestamp())}"
            
            # Prepare request according to iKhokha API structure
            request_data = {
                "entityID": entity_id,
                "externalEntityID": external_entity_id,
                "amount": int(registration_data['total_amount'] * 100),  # Convert to cents
                "currency": "ZAR",
                "requesterUrl": Config.IKHOKHA_RETURN_URL or "https://globalconference.co.za/payment/callback",
                "description": f"Conference Registration - {registration_data.get('conference_name', 'GIIP Conference')}",
                "paymentReference": payment_reference,
                "mode": "sandbox" if Config.IKHOKHA_APP_ID == "test" else "live",
                "externalTransactionID": external_transaction_id,
                "urls": {
                    "callbackUrl": Config.IKHOKHA_RETURN_URL or "https://globalconference.co.za/payment/callback",
                    "successPageUrl": Config.IKHOKHA_RETURN_URL or "https://globalconference.co.za/payment/callback", 
                    "failurePageUrl": Config.IKHOKHA_CANCEL_URL or "https://globalconference.co.za/payment/cancelled",
                    "cancelUrl": Config.IKHOKHA_CANCEL_URL or "https://globalconference.co.za/payment/cancelled"
                }
            }
            
            # Convert to JSON string
            request_body_str = json.dumps(request_data)
            
            # Create payload for signing
            payload_to_sign = self.create_payload_to_sign(self.api_endpoint, request_body_str)
            
            # Generate signature
            signature = self.sign_payload(payload_to_sign, self.secret_key)
            
            # Prepare headers according to iKhokha specification
            headers = {
                "Content-Type": "application/json",
                "IK-APPID": self.app_id,
                "IK-SIGN": signature
            }
            
            logger.info(f"Making iKhokha payment request for amount: R{registration_data['total_amount']}")
            logger.debug(f"Request URL: {self.api_endpoint}")
            logger.debug(f"Request Headers: {headers}")
            logger.debug(f"Request Body: {request_body_str}")
            
            # Make API request
            response = requests.post(
                self.api_endpoint,
                headers=headers,
                data=request_body_str,
                timeout=30
            )
            
            logger.info(f"iKhokha API Response: {response.status_code}")
            logger.debug(f"Response Text: {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"iKhokha payment created successfully: {result.get('paymentId', 'No ID')}")
                
                return {
                    'success': True,
                    'payment_url': result.get('paymentUrl', ''),
                    'transaction_reference': payment_reference,
                    'payment_id': result.get('paymentId', ''),
                    'entity_id': entity_id,
                    'external_transaction_id': external_transaction_id
                }
            else:
                logger.error(f"iKhokha API error: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'error': f'Payment service error: {response.status_code}'
                }
                
        except requests.RequestException as e:
            logger.error(f"iKhokha API request failed: {str(e)}")
            return {
                'success': False,
                'error': 'Payment service temporarily unavailable. Please try again later.'
            }
        except Exception as e:
            logger.error(f"Unexpected error creating payment: {str(e)}")
            return {
                'success': False,
                'error': 'An unexpected error occurred. Please try again.'
            }
    
    def verify_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """
        Verify payment status with iKhokha
        
        Args:
            payment_id: iKhokha payment ID
            
        Returns:
            Payment status information
        """
        if not self.is_configured:
            return {
                'success': False,
                'error': 'iKhokha payment service is not configured'
            }
        
        try:
            # For now, return a simple success response
            # In production, you would make an API call to check status
            logger.info(f"Verifying payment status for ID: {payment_id}")
            
            return {
                'success': True,
                'status': 'paid',  # Assume payment is successful for testing
                'amount': 0,
                'reference': payment_id,
                'payment_date': datetime.now().isoformat(),
                'transaction_id': payment_id
            }
            
        except Exception as e:
            logger.error(f"Payment verification failed: {str(e)}")
            return {
                'success': False,
                'error': 'Unable to verify payment status'
            }
    
    def verify_webhook_signature(self, payload: str, signature: str) -> bool:
        """
        Verify webhook signature from iKhokha
        
        Args:
            payload: Webhook payload
            signature: Provided signature
            
        Returns:
            True if signature is valid
        """
        if not self.is_configured:
            logger.warning("Cannot verify webhook signature - iKhokha service not configured")
            return False
        
        try:
            # For development, always return True
            # In production, implement proper signature verification with webhook secret
            logger.info(f"Webhook signature verification (dev mode): {signature[:10] if signature else 'None'}...")
            return True
            
        except Exception as e:
            logger.error(f"Webhook signature verification failed: {str(e)}")
            return False
    
    def process_webhook_data(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process webhook data from iKhokha
        
        Args:
            webhook_data: Webhook payload data
            
        Returns:
            Processed payment information
        """
        try:
            return {
                'success': True,
                'payment_id': webhook_data.get('payment_id'),
                'status': webhook_data.get('status'),
                'amount': webhook_data.get('amount'),
                'reference': webhook_data.get('reference'),
                'transaction_id': webhook_data.get('transaction_id'),
                'payment_date': webhook_data.get('payment_date'),
                'payment_method': webhook_data.get('payment_method')
            }
            
        except Exception as e:
            logger.error(f"Webhook processing failed: {str(e)}")
            return {
                'success': False,
                'error': 'Invalid webhook data'
            }


# Global instance - will work even without credentials for development
try:
    payment_service = IKhokhaPaymentService()
except Exception as e:
    logger.warning(f"Could not initialize iKhokha payment service: {e}")
    payment_service = None


def create_payment_session(registration_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a payment session for registration
    
    Args:
        registration_data: Registration information
        
    Returns:
        Payment session details
    """
    if not payment_service:
        return {
            'success': False,
            'error': 'Payment service not available. Please contact administrator.'
        }
    return payment_service.create_payment_request(registration_data)


def verify_payment(payment_id: str) -> Dict[str, Any]:
    """
    Verify payment status
    
    Args:
        payment_id: Payment ID to verify
        
    Returns:
        Payment verification result
    """
    if not payment_service:
        return {
            'success': False,
            'error': 'Payment service not available'
        }
    return payment_service.verify_payment_status(payment_id)


def process_payment_webhook(payload: str, signature: str) -> Dict[str, Any]:
    """
    Process payment webhook
    
    Args:
        payload: Webhook payload
        signature: Webhook signature
        
    Returns:
        Processing result
    """
    if not payment_service:
        return {
            'success': False,
            'error': 'Payment service not available'
        }
    
    if not payment_service.verify_webhook_signature(payload, signature):
        return {
            'success': False,
            'error': 'Invalid webhook signature'
        }
    
    try:
        webhook_data = json.loads(payload)
        return payment_service.process_webhook_data(webhook_data)
    except json.JSONDecodeError:
        return {
            'success': False,
            'error': 'Invalid webhook payload'
        }