from typing import Optional, Dict, Any, List
from bot.client import BinanceFuturesClient, BinanceAPIError
from bot.logging_config import logger

class OrderManager:
    """
    Manages order operations on Binance Futures Testnet using the provided BinanceFuturesClient.
    """
    def __init__(self, client: BinanceFuturesClient):
        self.client = client

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Places a futures order (MARKET, LIMIT, STOP_MARKET, or STOP_LIMIT).
        
        :param symbol: e.g. 'BTCUSDT'
        :param side: 'BUY' or 'SELL'
        :param order_type: 'MARKET', 'LIMIT', 'STOP_MARKET', 'STOP_LIMIT'
        :param quantity: The amount to trade
        :param price: The limit price (required for LIMIT and STOP_LIMIT)
        :param stop_price: The trigger price (required for STOP_MARKET and STOP_LIMIT)
        """
        logger.info(f"Placing {order_type} {side} order for {quantity} {symbol}...")
        
        # Build base params
        params: Dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": str(quantity),  # API requires string representations of decimals
        }

        # Handle specific order types
        if order_type == "LIMIT":
            if price is None:
                raise ValueError("Price is required for LIMIT orders.")
            params["price"] = str(price)
            params["timeInForce"] = "GTC"  # Good Till Cancelled
            
        elif order_type == "STOP_MARKET":
            if stop_price is None:
                raise ValueError("Stop Price is required for STOP_MARKET orders.")
            params["stopPrice"] = str(stop_price)
            # Some environments require timeInForce or workingType, default workingType is CONTRACT_PRICE
            
        elif order_type == "STOP_LIMIT":
            if price is None or stop_price is None:
                raise ValueError("Both Price and Stop Price are required for STOP_LIMIT orders.")
            params["price"] = str(price)
            params["stopPrice"] = str(stop_price)
            params["timeInForce"] = "GTC"

        try:
            response = self.client.send_request("POST", "/fapi/v1/order", params=params, signed=True)
            logger.info(f"Order placed successfully. ID: {response.get('orderId')}, Status: {response.get('status')}")
            return response
        except BinanceAPIError as e:
            logger.error(f"Failed to place order: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error while placing order: {e}")
            raise

    def get_order_status(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Queries the status of an existing order by its ID."""
        logger.info(f"Querying status for order {order_id} ({symbol})...")
        params = {
            "symbol": symbol,
            "orderId": order_id
        }
        return self.client.send_request("GET", "/fapi/v1/order", params=params, signed=True)

    def get_account_balances(self) -> List[Dict[str, Any]]:
        """
        Retrieves the account balance list.
        First tries the modern v3 endpoint; falls back to v2 if necessary.
        """
        logger.debug("Fetching account balances...")
        try:
            # Try V3 balance endpoint
            return self.client.send_request("GET", "/fapi/v3/balance", signed=True)
        except BinanceAPIError as e:
            # Fallback to V2 if server does not support V3 yet
            if e.status_code == 404 or "Invalid request" in str(e):
                logger.warning("v3/balance not available. Falling back to v2/balance...")
                return self.client.send_request("GET", "/fapi/v2/balance", signed=True)
            raise
