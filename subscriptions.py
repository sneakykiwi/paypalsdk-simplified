from paypalrestsdk import BillingPlan, BillingAgreement
import base64
import requests
from datetime import timedelta, datetime


class PayPal:
    def __init__(self, mode: str, client_id: str, client_secret: str):
        self.mode = mode
        self.client_id = client_id
        self.client_secret = client_secret


class Subscription(PayPal):
    def __init__(self, mode: str, client_id: str, client_secret: str, name: str = None, description: str = None,
                 auto_bill_amount: str = 'yes', cancel_url: str = None, initial_fail_amount_action: str = 'continue',
                 max_fail_attempts: str = '1', return_url: str = None, setup_fee: list = None, currency: str = None,
                 cost: str = None, cycles: int = 0, frequency: str = 'MONTH', frequency_interval: str = '1',
                 subscription_name: str = None, subscription_type: str = 'REGULAR',
                 billing_plan_type: str = 'INFINITE'):

        super().__init__(mode, client_id, client_secret)
        self.name = name
        self.description = description
        self.auto_bill_amount = auto_bill_amount
        self.cancel_url = cancel_url
        self.initial_fail_amount = initial_fail_amount_action
        self.max_fail_attempts = max_fail_attempts
        self.return_url = return_url
        self.setup_fee = setup_fee
        self.currency = currency
        self.cost = cost
        self.cycles = cycles
        self.frequency = frequency
        self.frequency_interval = frequency_interval
        self.subscription_name = subscription_name
        self.subscription_type = subscription_type
        self.billing_plan_type = billing_plan_type
        self.billing_plan_id = None
        self.billing_plan_attributes = {
            "name": f'{self.name}',
            "description": f'{self.description}',
            'merchant_preferences': {
                'auto_bill_amount': f'{self.auto_bill_amount}',
                'cancel_url': f'{self.cancel_url}',
                'initial_fail_amount_action': f"{self.initial_fail_amount}",
                "max_fail_attempts": f"{self.max_fail_attempts}",
                "return_url": f'{self.return_url}',
                'setup_fee': {
                    'currency': f'{self.currency}',
                    'value': f'{self.setup_fee}'
                }
            },
            'payment_definitions': [
                {
                    'amount': {
                        'currency': f'{self.currency}',
                        'value': f'{self.cost}'
                    },

                    "cycles": self.cycles,
                    "frequency": f'{self.frequency}',
                    'frequency_interval': f'{self.frequency_interval}',
                    'name': f'{self.subscription_type}',
                    'type': f'{self.subscription_type}'

                }],
            'type': f'{self.billing_plan_type}'}
        self.billing_plan = BillingPlan(self.billing_plan_attributes)

    def create(self):
        if self.billing_plan.create():
            self.billing_plan_id = self.billing_plan.id
            return True
        else:
            raise Exception(self.billing_plan.error)

    def activate(self):
        if self.billing_plan.create():
            return True
        else:
            raise Exception(self.billing_plan.error)

    def __get_paypal_access_token(self):
        if self.mode == 'live':
            url = "https://api.paypal.com/v1/oauth2/token"
        else:
            url = "https://api.sandbox.paypal.com/v1/oauth2/token"
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': f'Basic {base64.b64encode(f"{self.client_id}:{self.client_secret}")}'
        }
        payload = {'grant_type=client_credentials'}
        response = requests.request("POST", url, headers=headers, data=payload)
        try:
            token_data = response.json()
            return token_data['access_token']
        except Exception as e:
            raise Exception(
                f'An error has occured whilst getting the PayPal access token. Common problems with this are a mismatch of the client id and client secret. Error: {str(e)}')

    def __billing_agreement(self, description: str = f'Subscription agreement.'):
        billing_agreement = BillingAgreement({
            "name": self.name,
            "description": description,
            'start_type': (datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
            "plan":{
                'id': self.billing_plan_id
            },
            'payer':{
                'payment_method': 'paypal'
            }
        })
        if billing_agreement.create():
            for link in billing_agreement.links:
                if link.rel == 'approval_url':
                    approval_url = link.href
                    return approval_url
        else:
            raise Exception(billing_agreement.error)

    def cancel(self, reason: str = 'User cancellation.'):
        if not self.billing_plan_id:
            raise ValueError('Plan ID not found. Please create your subscription before trying to cancel it first!')
        headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {self.__get_paypal_access_token()}'}
        data = {'reason': reason}
        if self.mode == 'live':
            url = f'https://api.paypal.com/v1/billing/{self.billing_plan_id}/cancel'
        else:
            url = f'https://api.sandbox.paypal.com/v1/billing/{self.billing_plan_id}/cancel'
        response = requests.post(url=url, headers=headers, json=data)
        if response.ok:
            return
        else:
            raise Exception(f'There has been an issue with your request, here is the reply from PayPal: {response.text}')

    @classmethod
    def pay(cls, payment_token: str = None):
        if not payment_token:
            raise ValueError('Please provide a valid payment token in order to activate the subscriptions for the requested user.')
        billing_agreement_response = BillingAgreement.execute(payment_token)
        return 'Payment activated.'

