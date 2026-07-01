# Binance Futures Testnet (USDT-M) Trading Bot

A robust, structured Python-based trading bot that places orders on the Binance Futures Testnet (USDT-M). This application features input validation, a resilient connection layer with automated server-time clock offset synchronization, structured logging to a file, and a premium CLI experience using colors, spinners, tables, and an interactive guided wizard.

---

## Project Structure

The project is structured with a clear separation of concerns between the API layer, input validation, configuration, logging, and the command-line interface.

```
trading_bot/
│
├── bot/
│   ├── __init__.py         # Package level exports
│   ├── client.py           # Core HTTP Binance API Client with signature & time sync
│   ├── orders.py           # Order payload mapping and account balance queries
│   ├── validators.py       # Input validation rules (fail-fast checks)
│   └── logging_config.py   # Logging setup for files and console output
│
├── logs/
│   └── bot.log             # Generated application log file (appended on run)
│
├── cli.py                  # Entry point for Click + Rich + Questionary CLI
├── requirements.txt        # Third-party dependency list
├── .env.example            # Environment variables configuration template
└── .env                    # Active local environment variables
```

---

## Setup & Installation

### 1. Prerequisites
- **Python 3.8+** installed. (Tested on Python 3.14)
- Binance Futures Testnet API Key and Secret. Register and generate them here: [Binance Futures Testnet](https://testnet.binancefuture.com).

### 2. Install Dependencies
Initialize a virtual environment and install the required libraries:

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 3. Configure Credentials
Copy the environment variables template and insert your keys:

```bash
cp .env.example .env
```

Open `.env` in a text editor and update:
```env
BINANCE_API_KEY=your_actual_api_key
BINANCE_API_SECRET=your_actual_api_secret
BINANCE_BASE_URL=https://testnet.binancefuture.com
```

---

## How to Run

The bot supports **two modes of operation**: direct command-line arguments (for script automation) and an interactive guided wizard (for manual entry and enhanced UX).

### Mode A: Direct CLI Arguments (Automation)
Run the script with flags to execute orders directly.

#### 1. Place a MARKET Order
For a market order, only `symbol`, `side`, `type`, and `quantity` are required:
```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --qty 0.001
```

#### 2. Place a LIMIT Order
For a limit order, `price` is also required (and will trigger a validation error if omitted):
```bash
python cli.py --symbol BTCUSDT --side SELL --type LIMIT --qty 0.002 --price 45000
```

#### 3. Place a STOP_MARKET Order (Bonus)
Requires a `--stop-price` trigger:
```bash
python cli.py --symbol BTCUSDT --side BUY --type STOP_MARKET --qty 0.001 --stop-price 55000
```

#### 4. Place a STOP_LIMIT Order (Bonus)
Requires both limit `--price` and `--stop-price` trigger:
```bash
python cli.py --symbol BTCUSDT --side SELL --type STOP_LIMIT --qty 0.001 --price 54900 --sp 55000
```

---

### Mode B: Interactive Wizard (Enhanced UX)
If you run the script **without any arguments** or pass the `--interactive` / `-i` flag, it enters a visual guided wizard:

```bash
python cli.py
# OR
python cli.py -i
```

This wizard will guide you step-by-step:
1. Select/Type symbol (defaults to BTCUSDT).
2. Select side (BUY/SELL) via keyboard arrow keys.
3. Select order type (MARKET/LIMIT/STOP_MARKET/STOP_LIMIT).
4. Prompt for quantity, price, and stop price (only showing fields applicable to the chosen order type).
5. Validate and place the order with a loading spinner.

---

## Logging

All requests, responses, and internal warnings/errors are saved in a structured format in **`logs/bot.log`**.
- **Log Level**: `DEBUG` is logged to the file (containing full request details, response payloads, error traces, and offset calibrations).
- **Log Redaction**: API keys and HMAC signatures are **automatically redacted** inside log lines before being written to disk to protect sensitive data.
- **Log Rotation**: Logs rotate automatically once they reach 5MB (keeping up to 5 historical log backups) to prevent disk space exhaustion.

---

## Error & Exception Handling

The bot handles issues gracefully:
1. **Input Validation Errors**: Pre-validates types and patterns before hitting the API (e.g. negative quantities or missing prices for LIMIT orders).
2. **Clock Offset Sync**: Automatically requests Binance server time on startup and calculates local-to-server latency offsets. This bypasses the typical "Timestamp for this request is outside of the recvWindow" rejection due to local clock desynchronization.
3. **Binance API Rejections**: Traps Binance API custom codes (e.g. `-2015: Invalid API-key`, `-1013: Filter failure (invalid quantity/price step)`), formats them clearly for the user, and logs the payload.
4. **Network Failures**: Catches timeouts and connection losses and advises the user to check their connection.
