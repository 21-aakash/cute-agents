"""
External API clients layer.
"""
from learning.code_manual.Refundbot.app.clients.api_client import get_http_client, close_http_client, generate_request_id
from learning.code_manual.Refundbot.app.clients.order_api import OrderAPIClient
from learning.code_manual.Refundbot.app.clients.shipping_api import ShippingAPIClient

__all__ = [
    'get_http_client',
    'close_http_client', 
    'generate_request_id',
    'OrderAPIClient',
    'ShippingAPIClient'
]
