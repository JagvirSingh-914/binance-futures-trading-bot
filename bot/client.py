import time
import hmac
import hashlib
from urllib.parse import urlencode
import requests
from bot.logging_config import logger

class BinanceClientError(Exception):
    """Base exception for all Binance Client errors."""
    pass

class BinanceNetworkError(BinanceClientError):
    """Exception raised for network connectivity, timeout, or DNS issues."""
    pass

class BinanceAPIError(BinanceClientError):
    """Exception raised when Binance API returns an error response (status code >= 400)."""
    def __init__(self, status_code: int, code: int, message: str, response_body: str):
        super().__init__(f"Binance API Error {code}: {message} (HTTP {status_code})")
        self.status_code = status_code
        self.code = code
        self.message = message
        self.response_body = response_body

class BinanceAuthError(BinanceClientError):
    """Exception raised when API credentials are missing or invalid."""
    pass


class BinanceFuturesClient:
    """
    HTTP Client for Binance Futures Testnet (USDT-M).
    Handles time-sync, request signing, logging, and error parsing.
    """
    def __init__(self, api_key: str, api_secret: str, base_url: str = "https://testnet.binancefuture.com"):
        self.api_key = api_key.strip() if api_key else ""
        self.api_secret = api_secret.strip() if api_secret else ""
        self.base_url = base_url.rstrip('/')
        self.time_offset_ms = 0
        
        if not self.api_key or not self.api_secret:
            logger.warning("Binance API Key or Secret is missing. Signed requests will fail.")

    def sync_time(self):
        """
        Queries the Binance server time to calculate the offset between local time
        and server time, avoiding "Timestamp for this request is outside of the recvWindow" errors.
        """
        logger.debug("Syncing clock with Binance server...")
        try:
            url = f"{self.base_url}/fapi/v1/time"
            local_before_ms = int(time.time() * 1000)
            
            response = requests.get(url, timeout=10)
            
            local_after_ms = int(time.time() * 1000)
            # RTT (Round Trip Time) approximation
            rtt = (local_after_ms - local_before_ms) // 2
            
            if response.status_code == 200:
                server_time_ms = response.json().get("serverTime")
                self.time_offset_ms = server_time_ms - (local_before_ms + rtt)
                logger.info(f"Clock synced. Server offset: {self.time_offset_ms}ms (RTT: {rtt}ms)")
            else:
                logger.warning(f"Could not sync time. Server returned status {response.status_code}")
        except Exception as e:
            logger.warning(f"Failed to sync time due to network error: {e}. Using local system time.")

    def _get_timestamp(self) -> int:
        """Returns the current synchronized timestamp in milliseconds."""
        return int(time.time() * 1000) + self.time_offset_ms

    def _sign_payload(self, params: dict) -> str:
        """Generates the HMAC-SHA256 signature for the given parameters."""
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    def send_request(self, method: str, endpoint: str, params: dict = None, signed: bool = True) -> dict:
        """
        Sends an HTTP request to the Binance Futures API.
        
        :param method: HTTP Method (GET, POST, DELETE, etc.)
        :param endpoint: API Endpoint path (e.g. '/fapi/v1/order')
        :param params: Dictionary of parameters to pass
        :param signed: True if endpoint requires HMAC signature
        """
        method = method.upper()
        params = params.copy() if params else {}
        
        if signed:
            if not self.api_key or not self.api_secret:
                raise BinanceAuthError("API Key and Secret are required for signed endpoints.")
            
            params['timestamp'] = self._get_timestamp()
            params['signature'] = self._sign_payload(params)

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "X-MBX-APIKEY": self.api_key if self.api_key else ""
        }

        url = f"{self.base_url}{endpoint}"
        
        # Redact signature for logging
        log_params = params.copy()
        if 'signature' in log_params:
            log_params['signature'] = "[REDACTED_SIGNATURE]"
            
        logger.debug(f"API Request: {method} {url} - Params: {log_params}")

        try:
            if method in ("GET", "DELETE"):
                response = requests.request(method, url, params=params, headers=headers, timeout=15)
            elif method in ("POST", "PUT"):
                response = requests.request(method, url, data=params, headers=headers, timeout=15)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during API Request: {e}")
            raise BinanceNetworkError(f"Network communication failed: {e}") from e

        logger.debug(f"API Response status: {response.status_code}")
        
        try:
            response_json = response.json()
        except ValueError:
            logger.error(f"Non-JSON response received (HTTP {response.status_code}): {response.text}")
            raise BinanceAPIError(
                status_code=response.status_code,
                code=-1,
                message="Non-JSON response from server",
                response_body=response.text
            )

        if response.status_code >= 400:
            error_code = response_json.get("code", -1)
            error_msg = response_json.get("msg", "Unknown error")
            logger.error(f"Binance API returned error status {response.status_code}: code={error_code}, msg='{error_msg}'")
            raise BinanceAPIError(
                status_code=response.status_code,
                code=error_code,
                message=error_msg,
                response_body=response.text
            )

        logger.debug(f"API Response data: {response_json}")
        return response_json
