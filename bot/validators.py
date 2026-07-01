import re

class ValidationError(ValueError):
    """Custom exception raised for validation errors on inputs."""
    pass

def validate_symbol(symbol: str) -> str:
    """
    Validates a trading symbol.
    Should be uppercase, alphanumeric, and typically end with USDT or BUSD for USDT-M.
    """
    if not symbol:
        raise ValidationError("Symbol cannot be empty.")
    
    clean_symbol = symbol.strip().upper()
    
    # Binance symbols are alphanumeric
    if not re.match(r"^[A-Z0-9]{3,15}$", clean_symbol):
        raise ValidationError(
            f"Invalid symbol format: '{symbol}'. Must be alphanumeric and 3-15 chars long (e.g. BTCUSDT)."
        )
    return clean_symbol

def validate_side(side: str) -> str:
    """Validates the order side (BUY or SELL)."""
    if not side:
        raise ValidationError("Order side cannot be empty.")
    
    clean_side = side.strip().upper()
    if clean_side not in ("BUY", "SELL"):
        raise ValidationError(f"Invalid side: '{side}'. Must be either 'BUY' or 'SELL'.")
    return clean_side

def validate_order_type(order_type: str) -> str:
    """Validates the order type."""
    if not order_type:
        raise ValidationError("Order type cannot be empty.")
    
    clean_type = order_type.strip().upper()
    valid_types = ("LIMIT", "MARKET", "STOP_MARKET", "STOP_LIMIT")
    if clean_type not in valid_types:
        raise ValidationError(
            f"Invalid order type: '{order_type}'. Must be one of {', '.join(valid_types)}."
        )
    return clean_type

def validate_quantity(quantity: str) -> float:
    """Validates that quantity is a positive float."""
    if not quantity:
        raise ValidationError("Quantity cannot be empty.")
    try:
        val = float(quantity)
    except ValueError:
        raise ValidationError(f"Invalid quantity: '{quantity}'. Must be a valid number.")
    
    if val <= 0:
        raise ValidationError(f"Quantity must be greater than zero. Got {val}.")
    return val

def validate_price(price: str, order_type: str) -> float:
    """
    Validates that price is a positive float if order type is LIMIT or STOP_LIMIT.
    Otherwise returns 0.0 or None.
    """
    if order_type in ("LIMIT", "STOP_LIMIT"):
        if not price:
            raise ValidationError(f"Price is required for '{order_type}' orders.")
        try:
            val = float(price)
        except ValueError:
            raise ValidationError(f"Invalid price: '{price}'. Must be a valid number.")
        if val <= 0:
            raise ValidationError(f"Price must be greater than zero. Got {val}.")
        return val
    return 0.0

def validate_stop_price(stop_price: str, order_type: str) -> float:
    """
    Validates that stopPrice is a positive float if order type is STOP_MARKET or STOP_LIMIT.
    Otherwise returns 0.0 or None.
    """
    if order_type in ("STOP_MARKET", "STOP_LIMIT"):
        if not stop_price:
            raise ValidationError(f"Stop Price (--stop-price) is required for '{order_type}' orders.")
        try:
            val = float(stop_price)
        except ValueError:
            raise ValidationError(f"Invalid stop price: '{stop_price}'. Must be a valid number.")
        if val <= 0:
            raise ValidationError(f"Stop price must be greater than zero. Got {val}.")
        return val
    return 0.0

def validate_all(symbol: str, side: str, order_type: str, quantity: str, price: str = None, stop_price: str = None) -> dict:
    """
    Runs all validators and returns clean, parsed inputs as a dictionary.
    Raises ValidationError if any check fails.
    """
    clean_symbol = validate_symbol(symbol)
    clean_side = validate_side(side)
    clean_type = validate_order_type(order_type)
    clean_qty = validate_quantity(quantity)
    clean_price = validate_price(price, clean_type)
    clean_stop_price = validate_stop_price(stop_price, clean_type)
    
    return {
        "symbol": clean_symbol,
        "side": clean_side,
        "type": clean_type,
        "quantity": clean_qty,
        "price": clean_price if clean_type in ("LIMIT", "STOP_LIMIT") else None,
        "stopPrice": clean_stop_price if clean_type in ("STOP_MARKET", "STOP_LIMIT") else None,
    }
