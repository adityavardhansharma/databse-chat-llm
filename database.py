import os
from supabase import create_client
from dotenv import load_dotenv
from models import User
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    logger.error("Supabase credentials not found in environment variables")
    raise ValueError("Supabase credentials not found in environment variables")

try:
    supabase = create_client(supabase_url, supabase_key)
    logger.info("Supabase client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Supabase client: {str(e)}")
    raise


def get_user_by_name(name):

    try:
        response = supabase.table("table_name").select("*").eq("name", name).execute()

        if response.data and len(response.data) > 0:
            user_data = response.data[0]
            return User(**user_data)
        return None
    except Exception as e:
        logger.error(f"Error retrieving user by name: {str(e)}")
        raise


def get_all_users():

    try:
        response = supabase.table("table_name").select("*").execute()

        if response.data:
            return [User(**user_data) for user_data in response.data]
        return []
    except Exception as e:
        logger.error(f"Error retrieving all users: {str(e)}")
        raise


def search_users(query_params):

    try:
        query = supabase.table("table_name").select("*")

        for field, value in query_params.items():
            query = query.eq(field, value)

        response = query.execute()

        if response.data:
            return [User(**user_data) for user_data in response.data]
        return []
    except Exception as e:
        logger.error(f"Error searching users: {str(e)}")
        raise
