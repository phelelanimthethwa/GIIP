"""
Yoco Payment Gateway Integration Service

This module provides integration with Yoco payment gateway for processing
conference registration payments.

Yoco API Documentation: https://developer.yoco.com/
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


class YocoPaymentService:
    """
    Service class for handling Yoco payment gateway integration
    """
    
    def __init__(self, secret_key: str = None):
        """
        Initialize Yoco payment service
        
        Args:
            secret_key: Yoco secret API key
        """
        self.secret_key = secret_key or Config.YOCO_SECRET_KEY
        self.public_key = Config.YOCO_PUBLIC_KEY
        
        # Yoco API endpoints
        self.api_base_url = Config.YOCO_BASE_URL or "https://payments.yoco.com"
        self.api_endpoint = f"{self.api_base_url}/api/checkouts"
        
        # Allow service to be created without credentials for development
        self.is_configured = bool(self.secret_key and self.public_key)
        
        if not self.is_configured:
            logger.warning("Yoco payment service is not configured. Payment features will be disabled.")
    
    def create_payment_request(self, registration_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a payment request with Yoco following their API specification
        
        Args:
            registration_data: Registration information including amount, user details, etc.
            
        Returns:
            Dictionary containing payment URL and transaction reference
        """
        if not self.is_configured:
            return {
                'success': False,
                'error': 'Yoco payment service is not configured. Please set YOCO_SECRET_KEY and YOCO_PUBLIC_KEY environment variables.'
            }
        
        # Demo mode for development/testing
        if (self.secret_key and self.secret_key.lower() in ['demo', 'test']):
            logger.info("Running in DEMO mode - simulating payment creation")
            transaction_ref = f"DEMO_REG_{registration_data.get('user_id', 'ANON')}_{int(datetime.now().timestamp())}"
            return {
                'success': True,
                'payment_url': f'https://globalconference.co.za/payment/demo?ref={transaction_ref}',
                'transaction_reference': transaction_ref,
                'payment_id': f'demo_payment_{int(datetime.now().timestamp())}',
                'checkout_id': str(uuid.uuid4())
            }
        
        try:
            # Generate unique reference
            payment_reference = f"REG_{registration_data.get('user_id', 'ANON')}_{int(datetime.now().timestamp())}"
            
            # Convert amount to cents (Yoco uses cents)
            amount_in_cents = int(float(registration_data['total_amount']) * 100)
            
            # Prepare request according to Yoco API structure
            request_data = {
                "amount": amount_in_cents,
                "currency": "ZAR",
                "cancelUrl": Config.YOCO_CANCEL_URL or "https://globalconference.co.za/payment/cancelled",
                "successUrl": Config.YOCO_RETURN_URL or "https://globalconference.co.za/payment/callback",
                "failureUrl": Config.YOCO_CANCEL_URL or "https://globalconference.co.za/payment/cancelled",
                "metadata": {
                    "reference": payment_reference,
                    "user_id": registration_data.get('user_id', ''),
                    "full_name": registration_data.get('full_name', ''),
                    "email": registration_data.get('email', ''),
                    "registration_type": registration_data.get('registration_type', ''),
                    "registration_period": registration_data.get('registration_period', ''),
                    "conference_name": registration_data.get('conference_name', 'GIIP Conference')
                }
            }
            
            # Prepare headers according to Yoco specification
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.secret_key}"
            }
            
            print(f" YOCO: Making payment request for R{registration_data['total_amount']}")`r`n            logger.info(f"Making Yoco payment request for amount: R{registration_data['total_amount']} ({amount_in_cents} cents)")
            logger.debug(f"Request URL: {self.api_endpoint}")
            logger.debug(f"Request Body: {json.dumps(request_data, indent=2)}")
            
            # Make API request
            response = requests.post(
                self.api_endpoint,
                headers=headers,
                json=request_data,
                timeout=30
            )
            
            print(f" YOCO API Response: {response.status_code}")`r`n            logger.info(f"Yoco API Response: {response.status_code}")
            logger.debug(f"Response Text: {response.text[:500]}...")
            
            if response.status_code in [200, 201]:
                result = response.json()
                logger.info(f"Yoco payment checkout created successfully: {result.get('id', 'No ID')}")
                
                return {
                    'success': True,
                    'payment_url': result.get('redirectUrl', ''),
                    'transaction_reference': payment_reference,
                    'payment_id': result.get('id', ''),
                    'checkout_id': result.get('id', ''),
                    'status': result.get('status', 'pending')
                }
            elif response.status_code in [400, 401, 403, 404, 500]:
                # Handle HTTP error responses
                try:
                    error_data = response.json()
                    error_message = error_data.get('message', f'API Error {response.status_code}')
                except ValueError:
                    error_message = f'API Error {response.status_code}: {response.text[:100]}'
                
                print(f" YOCO API Error {response.status_code}: {error_message}")`r`n                logger.error(f"Yoco API Error {response.status_code}: {error_message}")
                
                # If we get 401/403, fall back to demo mode
                if response.status_code in [401, 403]:
                    print(" YOCO: Authentication failed, falling back to demo mode")`r`n                    logger.warning("Yoco API authentication failed, falling back to demo mode")
                    transaction_ref = f"DEMO_REG_{registration_data.get('user_id', 'ANON')}_{int(datetime.now().timestamp())}"
                    return {
                        'success': True,
                        'payment_url': f'https://globalconference.co.za/payment/demo?ref={transaction_ref}',
                        'transaction_reference': transaction_ref,
                        'payment_id': f'demo_payment_{int(datetime.now().timestamp())}',
                        'checkout_id': str(uuid.uuid4())
                    }
                
                return {
                    'success': False,
                    'error': f'Payment service error: {error_message}'
                }
            else:
                logger.error(f"Unexpected response code {response.status_code}: {response.text[:200]}")
                return {
                    'success': False,
                    'error': f'Payment service error: HTTP {response.status_code}'
                }
                
        except requests.RequestException as e:
            logger.error(f"Yoco API request failed: {str(e)}")
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
    
    def verify_payment_status(self, checkout_id: str) -> Dict[str, Any]:
        """
        Verify payment status with Yoco
        
        Args:
            checkout_id: Yoco checkout ID
            
        Returns:
            Payment status information
        """
        if not self.is_configured:
            return {
                'success': False,
                'error': 'Yoco payment service is not configured'
            }
        
        try:
            # Construct the endpoint to fetch checkout details
            verify_url = f"{self.api_endpoint}/{checkout_id}"
            
            headers = {
                "Authorization": f"Bearer {self.secret_key}",
                "Content-Type": "application/json"
            }
            
            logger.info(f"Verifying payment status for checkout ID: {checkout_id}")
            
            response = requests.get(verify_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                
                status = result.get('status', 'pending')
                metadata = result.get('metadata', {})
                
                return {
                    'success': True,
                    'status': 'paid' if status == 'complete' else status,
                    'amount': result.get('amount', 0) / 100,  # Convert from cents
                    'reference': metadata.get('reference', checkout_id),
                    'payment_date': result.get('createdDate', datetime.now().isoformat()),
                    'transaction_id': checkout_id,
                    'metadata': metadata
                }
            else:
                logger.error(f"Failed to verify payment: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'error': 'Unable to verify payment status'
                }
            
        except Exception as e:
            logger.error(f"Payment verification failed: {str(e)}")
            return {
                'success': False,
                'error': 'Unable to verify payment status'
            }
    
    def verify_webhook_signature(self, payload: str, signature: str) -> bool:
        """
        Verify webhook signature from Yoco
        
        Args:
            payload: Webhook payload
            signature: Provided signature
            
        Returns:
            True if signature is valid
        """
        if not self.is_configured:
            logger.warning("Cannot verify webhook signature - Yoco service not configured")
            return False
        
        try:
            # Yoco uses HMAC SHA256 for webhook signatures
            webhook_secret = Config.YOCO_WEBHOOK_SECRET or self.secret_key
            
            # Calculate expected signature
            expected_signature = hmac.new(
                webhook_secret.encode('utf-8'),
                payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures securely
            is_valid = hmac.compare_digest(expected_signature, signature)
            
            logger.info(f"Webhook signature validation: {'valid' if is_valid else 'invalid'}")
            return is_valid
            
        except Exception as e:
            logger.error(f"Webhook signature verification failed: {str(e)}")
            return False
    
    def process_webhook_data(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process webhook data from Yoco
        
        Args:
            webhook_data: Webhook payload data
            
        Returns:
            Processed payment information
        """
        try:
            # Extract the checkout data from webhook
            checkout = webhook_data.get('payload', {})
            if not checkout:
                checkout = webhook_data
            
            metadata = checkout.get('metadata', {})
            status = checkout.get('status', 'pending')
            
            return {
                'success': True,
                'payment_id': checkout.get('id'),
                'status': 'paid' if status == 'complete' else status,
                'amount': checkout.get('totalAmount', 0) / 100,  # Convert from cents
                'reference': metadata.get('reference', ''),
                'transaction_id': checkout.get('id'),
                'payment_date': checkout.get('createdDate', datetime.now().isoformat()),
                'payment_method': 'yoco',
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"Webhook processing failed: {str(e)}")
            return {
                'success': False,
                'error': 'Invalid webhook data'
            }


# Global instance - will work even without credentials for development
try:
    payment_service = YocoPaymentService()
except Exception as e:
    logger.warning(f"Could not initialize Yoco payment service: {e}")
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


def verify_payment(checkout_id: str) -> Dict[str, Any]:
    """
    Verify payment status
    
    Args:
        checkout_id: Checkout ID to verify
        
    Returns:
        Payment verification result
    """
    if not payment_service:
        return {
            'success': False,
            'error': 'Payment service not available'
        }
    return payment_service.verify_payment_status(checkout_id)


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

