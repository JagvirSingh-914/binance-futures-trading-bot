import os
import sys
import logging
from typing import Optional
import click
from dotenv import load_dotenv

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.status import Status
from rich.theme import Theme

import questionary

# Ensure parent directory is in path for relative imports if run directly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bot.logging_config import setup_logging
from bot.client import BinanceFuturesClient, BinanceAPIError, BinanceNetworkError, BinanceAuthError
from bot.validators import validate_all, ValidationError
from bot.orders import OrderManager

# Define custom rich theme for a premium feel
custom_theme = Theme({
    "info": "dim cyan",
    "warning": "magenta",
    "danger": "bold red",
    "success": "bold green",
    "accent": "bold yellow"
})

console = Console(theme=custom_theme)

# Load environment variables
load_dotenv()

# Setup logging
setup_logging(log_filename="trading.log")
logger = logging.getLogger("trading_bot")


def get_client() -> Optional[BinanceFuturesClient]:
    """Helper to initialize the Binance Client using environment variables."""
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    base_url = os.getenv("BINANCE_BASE_URL", "https://testnet.binancefuture.com")

    if not api_key or not api_secret:
        console.print(Panel.fit(
            "[danger]Error: Binance API Key or Secret is missing![/danger]\n\n"
            "Please create a [accent].env[/accent] file in the root directory with:\n"
            "  [info]BINANCE_API_KEY=your_key[/info]\n"
            "  [info]BINANCE_API_SECRET=your_secret[/info]\n"
            "  [info]BINANCE_BASE_URL=https://testnet.binancefuture.com[/info]\n\n"
            "Refer to the [accent]README.md[/accent] for details.",
            title="Configuration Required",
            border_style="red"
        ))
        logger.error("Failed to initialize client: Missing API credentials.")
        return None

    return BinanceFuturesClient(api_key=api_key, api_secret=api_secret, base_url=base_url)


def print_order_summary(symbol: str, side: str, order_type: str, quantity: float, price: Optional[float], stop_price: Optional[float]):
    """Prints a beautiful summary of the request before sending it."""
    console.print(Panel(
        f"[info]Symbol:[/info] [accent]{symbol}[/accent]\n"
        f"[info]Side:[/info] [{'green' if side == 'BUY' else 'red'}]{side}[/]\n"
        f"[info]Type:[/info] [cyan]{order_type}[/cyan]\n"
        f"[info]Quantity:[/info] [white]{quantity}[/white]\n"
        f"{f'[info]Price:[/info] [white]{price}[/white]' if price else ''}"
        f"{f'[info]Stop Price:[/info] [white]{stop_price}[/white]' if stop_price else ''}",
        title="Order Request Summary",
        border_style="cyan"
    ))


def display_order_response(response: dict):
    """Renders the Binance API response into a beautiful, styled console table."""
    order_id = response.get("orderId")
    symbol = response.get("symbol")
    side = response.get("side")
    order_type = response.get("type")
    status = response.get("status")
    executed_qty = response.get("executedQty", "0.0")
    avg_price = response.get("avgPrice", "0.0")
    if float(avg_price) == 0.0:
        avg_price = response.get("price", "0.0")  # Fallback to limit price if avg is 0.0

    table = Table(title="Order Response Details", border_style="green")
    table.add_column("Parameter", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Order ID", str(order_id))
    table.add_row("Symbol", str(symbol))
    table.add_row("Side", str(side), style="green" if side == "BUY" else "red")
    table.add_row("Order Type", str(order_type))
    table.add_row("Status", str(status), style="success" if status == "FILLED" else "accent")
    table.add_row("Executed Qty", str(executed_qty))
    table.add_row("Avg Execution Price", f"{avg_price} USDT")
    table.add_row("Client Order ID", str(response.get("clientOrderId")))

    console.print("\n", table)
    console.print(Panel(
        f"[success]✔ Success![/success] Order [accent]{order_id}[/accent] has been placed successfully with status [success]{status}[/success].",
        border_style="green"
    ))


def run_interactive_wizard():
    """Guided interactive CLI prompt for placing orders."""
    console.print(Panel(
        "Welcome to the [accent]Binance Futures Trading Bot Wizard[/accent]!\n"
        "Follow the steps below to place your order on the Testnet.",
        border_style="cyan"
    ))
    
    # 1. Select Symbol
    symbol = questionary.text(
        "Enter symbol (e.g. BTCUSDT, ETHUSDT):",
        default="BTCUSDT",
        validate=lambda text: True if len(text.strip()) > 0 else "Symbol is required."
    ).ask()
    if not symbol:
        return

    # 2. Select Side
    side = questionary.select(
        "Select Side:",
        choices=["BUY", "SELL"]
    ).ask()
    if not side:
        return

    # 3. Select Type
    order_type = questionary.select(
        "Select Order Type:",
        choices=["MARKET", "LIMIT", "STOP_MARKET", "STOP_LIMIT"]
    ).ask()
    if not order_type:
        return

    # 4. Quantity
    quantity = questionary.text(
        "Enter Quantity (e.g. 0.001):",
        validate=lambda text: True if re.match(r"^\d*\.?\d+$", text) else "Please enter a valid positive number."
    ).ask()
    if not quantity:
        return

    # 5. Price (if Limit/Stop-Limit)
    price = None
    if order_type in ("LIMIT", "STOP_LIMIT"):
        price = questionary.text(
            "Enter Limit Price (USDT):",
            validate=lambda text: True if re.match(r"^\d*\.?\d+$", text) else "Please enter a valid positive price."
        ).ask()
        if not price:
            return

    # 6. Stop Price (if Stop-Market/Stop-Limit)
    stop_price = None
    if order_type in ("STOP_MARKET", "STOP_LIMIT"):
        stop_price = questionary.text(
            "Enter Stop Trigger Price (USDT):",
            validate=lambda text: True if re.match(r"^\d*\.?\d+$", text) else "Please enter a valid positive trigger price."
        ).ask()
        if not stop_price:
            return

    # Execute
    execute_order_flow(
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=quantity,
        price=price,
        stop_price=stop_price
    )


def execute_order_flow(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str,
    price: Optional[str] = None,
    stop_price: Optional[str] = None
):
    """Orchestrates validation, client initialization, API call, and output rendering."""
    # 1. Validation
    try:
        inputs = validate_all(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price
        )
    except ValidationError as e:
        console.print(Panel(f"[danger]Input Validation Error:[/danger] {e}", border_style="red"))
        logger.error(f"Input Validation Failure: {e}")
        sys.exit(1)

    # 2. Client Init
    client = get_client()
    if not client:
        sys.exit(1)

    # 3. Connection & Time Sync (Spinner)
    with Status("[info]Connecting to Binance Futures Testnet and syncing clock...[/info]", console=console) as status:
        client.sync_time()
        manager = OrderManager(client)
        
        # Optionally show balances for context
        try:
            balances = manager.get_account_balances()
            usdt_balance = next((b for b in balances if b.get('asset') == 'USDT'), None)
            if usdt_balance:
                wallet_bal = float(usdt_balance.get('balance', 0))
                avail_bal = float(usdt_balance.get('availableBalance', 0))
                console.print(f"[info]Account Balance:[/info] {wallet_bal:.2f} USDT (Available: {avail_bal:.2f} USDT)")
        except Exception as e:
            logger.warning(f"Could not retrieve balances: {e}")

    # 4. Display Request Summary
    print_order_summary(
        symbol=inputs["symbol"],
        side=inputs["side"],
        order_type=inputs["type"],
        quantity=inputs["quantity"],
        price=inputs["price"],
        stop_price=inputs["stopPrice"]
    )

    # 5. Place Order (Spinner)
    try:
        with Status("[info]Sending order payload to Binance Futures Testnet...[/info]", console=console) as status:
            response = manager.place_order(
                symbol=inputs["symbol"],
                side=inputs["side"],
                order_type=inputs["type"],
                quantity=inputs["quantity"],
                price=inputs["price"],
                stop_price=inputs["stopPrice"]
            )
        display_order_response(response)
        
    except BinanceAuthError as e:
        console.print(Panel(f"[danger]Authentication Error:[/danger]\n{e}\nPlease check your API keys.", border_style="red"))
        sys.exit(1)
    except BinanceNetworkError as e:
        console.print(Panel(f"[danger]Network / Connectivity Error:[/danger]\n{e}", border_style="red"))
        sys.exit(1)
    except BinanceAPIError as e:
        console.print(Panel(
            f"[danger]Binance API Error (Code {e.code}):[/danger]\n{e.message}",
            title="Order Rejected",
            border_style="red"
        ))
        sys.exit(1)
    except Exception as e:
        console.print(Panel(f"[danger]Unexpected Error occurred:[/danger]\n{e}", border_style="red"))
        logger.exception("An unhandled exception occurred.")
        sys.exit(1)


import re  # Ensure re is imported for interactive regex validate

@click.command(help="Binance Futures USDT-M Testnet Trading Bot CLI.")
@click.option("--symbol", "-s", help="Trading pair symbol (e.g. BTCUSDT).")
@click.option("--side", "-d", type=click.Choice(["BUY", "SELL"], case_sensitive=False), help="Order side.")
@click.option("--type", "-t", "order_type", type=click.Choice(["LIMIT", "MARKET", "STOP_MARKET", "STOP_LIMIT"], case_sensitive=False), help="Order type.")
@click.option("--quantity", "-q", help="Order quantity.")
@click.option("--price", "-p", help="Limit price (required for LIMIT and STOP_LIMIT).")
@click.option("--stop-price", "-sp", help="Stop trigger price (required for STOP_MARKET and STOP_LIMIT).")
@click.option("--interactive", "-i", is_flag=True, help="Enter guided wizard interactive mode.")
def main(symbol, side, order_type, quantity, price, stop_price, interactive):
    # Check if we should enter interactive mode
    # Trigger if explicitly requested, or if no arguments are provided
    if interactive or not (symbol or side or order_type or quantity):
        run_interactive_wizard()
    else:
        # Require all basic options if executing in direct CLI mode
        if not symbol or not side or not order_type or not quantity:
            console.print("[danger]Error: Missing required arguments for CLI execution.[/danger]")
            console.print("Provide all of: --symbol, --side, --type, --quantity")
            console.print("Or run in interactive mode with: [accent]python cli.py -i[/accent] (or run without arguments)")
            sys.exit(1)
            
        execute_order_flow(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price
        )

if __name__ == "__main__":
    main()
