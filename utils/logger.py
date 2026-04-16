# utils/logger.py
# -----------------------------------------------------------------
# 로깅 시스템 (iWanted 패턴)
# -----------------------------------------------------------------

import logging
import os
from datetime import datetime


def setup_logger(log_dir: str = './logs', log_level: str = 'INFO') -> logging.Logger:
    os.makedirs(log_dir, exist_ok=True)

    log_filename = os.path.join(
        log_dir,
        f"{datetime.now().strftime('%Y-%m-%d')}.log"
    )

    level = getattr(logging, log_level.upper(), logging.INFO)

    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(level)
    stream_handler.setFormatter(formatter)

    _logger = logging.getLogger('imessage-pet')
    _logger.setLevel(level)
    _logger.handlers.clear()
    _logger.addHandler(file_handler)
    _logger.addHandler(stream_handler)

    return _logger


try:
    from config import LOG_DIR, LOG_LEVEL
    logger = setup_logger(LOG_DIR, LOG_LEVEL)
except ImportError:
    logger = setup_logger()
