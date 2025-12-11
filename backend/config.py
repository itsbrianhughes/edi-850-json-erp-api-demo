"""
Configuration Settings
"""

import os
from pathlib import Path

# Project root directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Database
DATABASE_PATH = BASE_DIR / "backend" / "db" / "integration.db"

# Logs
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Sample data
SAMPLE_DATA_DIR = BASE_DIR / "sample_data"

# API Configuration
MOCK_ERP_API_BASE_URL = "http://localhost:8000/api/erp"

# Retry Configuration
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2

# EDI Parsing
EDI_SEGMENT_DELIMITER = "~"
EDI_ELEMENT_DELIMITER = "*"
EDI_SUBELEMENT_DELIMITER = ":"
