"""
utils/supabase_client.py
========================
Dedicated Supabase PostgreSQL Connection Client & Health Check Module.

- Loads SUPABASE_URL and SUPABASE_KEY safely from environment variables (.env).
- Fails gracefully if configuration or credentials are missing or invalid.
- Exposes test_supabase_connection() for safe read-only health checks.
"""

import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env file if present
load_dotenv()

_supabase_client = None

def get_supabase_client():
    """
    Initialize and return the singleton Supabase client instance.
    Returns None if SUPABASE_URL or SUPABASE_KEY is missing or if initialization fails.
    """
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    supabase_url = os.environ.get('SUPABASE_URL', '').strip()
    supabase_key = os.environ.get('SUPABASE_KEY', '').strip()

    if not supabase_url or not supabase_key:
        logger.warning("[!] Supabase configuration missing (SUPABASE_URL or SUPABASE_KEY not set).")
        return None

    try:
        from supabase import create_client
        _supabase_client = create_client(supabase_url, supabase_key)
        logger.info("[+] Supabase client initialized successfully.")
        return _supabase_client
    except Exception as e:
        logger.error(f"[!] Failed to initialize Supabase client: {e}")
        return None

def test_supabase_connection():
    """
    Perform a safe read-only query to test database connectivity.
    Does NOT modify, insert, or delete any data.
    
    Returns:
        tuple: (bool success, str message)
    """
    client = get_supabase_client()
    if not client:
        supabase_url = os.environ.get('SUPABASE_URL', '').strip()
        supabase_key = os.environ.get('SUPABASE_KEY', '').strip()
        if not supabase_url or not supabase_key:
            return False, "Supabase: Configuration Missing (SUPABASE_URL / SUPABASE_KEY)"
        return False, "Supabase: Initialization Error"

    try:
        # Perform safe read-only limit(1) query on users table
        response = client.table("users").select("id").limit(1).execute()
        return True, "Supabase: Connected"
    except Exception as e:
        logger.error(f"[!] Supabase test connection failed: {e}")
        return False, f"Supabase Connection Failed: {str(e)}"
