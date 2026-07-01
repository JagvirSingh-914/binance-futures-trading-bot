import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging(log_filename="trading.log", console_level=logging.INFO, file_level=logging.DEBUG):
    """
    Sets up logging configuration.
    Logs DEBUG and above to a rotating file inside the logs/ directory.
    Logs INFO and above to the console.
    """
    logger = logging.getLogger("trading_bot")
    logger.setLevel(logging.DEBUG)  # Capture all logs at the root level

    # Avoid adding duplicate handlers if setup is called multiple times
    if logger.handlers:
        return logger

    # Resolve paths relative to the project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logs_dir = os.path.join(project_root, "logs")
    
    # Ensure logs directory exists
    os.makedirs(logs_dir, exist_ok=True)
    
    log_file_path = os.path.join(logs_dir, log_filename)

    file_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - [%(filename)s:%(lineno)d] - %(message)s"
    )
    console_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S"
    )

    # 1. File Handler (Rotating, keeps up to 5 files of 5MB each)
    try:
        file_handler = RotatingFileHandler(
            log_file_path, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setLevel(file_level)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Could not set up file logging: {e}")

    # 2. Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger

# Create a default logger instance
logger = logging.getLogger("trading_bot")
