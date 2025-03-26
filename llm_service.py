import os
import requests
import json
from dotenv import load_dotenv
import logging
from database import get_user_by_name, get_all_users, search_users

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Groq API credentials
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

if not GROQ_API_KEY:
    logger.error("Groq API key not found in environment variables")
    raise ValueError("Groq API key not found in environment variables")


def call_groq_api(messages, response_format=None):
    """
    Call the Groq API with the given messages.

    Args:
        messages (list): List of message objects with role and content.
        response_format (dict, optional): Format specification for the response.

    Returns:
        dict: The API response.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROQ_API_KEY}"
    }

    payload = {
        "model": "qwen-2.5-coder-32b",
        "messages": messages
    }

    if response_format:
        payload["response_format"] = response_format

    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error calling Groq API: {str(e)}")
        raise


def parse_user_query(query):
    """
    Use Groq's Gemma model to understand the user's intent and extract explicit search criteria.

    Args:
        query (str): The user's natural language query.

    Returns:
        dict: A dictionary containing the parsed intent and parameters.
    """
    try:
        system_prompt = """
You are a precise query parser for a user database. Extract ONLY the explicitly mentioned search criteria from the query. 
The database has a table with the following fields:
id, name, age, gender, phone_no, pincode, address.
Return a JSON object with these keys:
{
  "name": string or null,
  "location": string or null,
  "min_age": number or null,
  "max_age": number or null,
  "fields_requested": ["list", "of", "requested", "fields"],
  "is_all_info": true/false
}
Be literal — include only criteria explicitly stated.
Your response must be valid JSON only, with no additional text.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]
        response = call_groq_api(messages)
        parsed_intent_text = response["choices"][0]["message"]["content"]
        logger.info(f"Raw parsed intent: {parsed_intent_text}")

        try:
            parsed_intent = json.loads(parsed_intent_text)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'({.*})', parsed_intent_text, re.DOTALL)
            if json_match:
                parsed_intent = json.loads(json_match.group(1))
            else:
                raise ValueError("Could not extract valid JSON from LLM response")
        logger.info(f"Parsed intent: {parsed_intent}")
        return parsed_intent
    except Exception as e:
        logger.error(f"Error parsing user query: {str(e)}")
        raise


def generate_response(query, user_data=None):
    """
    Generate a natural language response based on the user's query and the retrieved data.

    This function dynamically builds the context using all available fields from the JSON data
    (which is generated via the Pydantic User model). The system prompt instructs the LLM to analyze
    the data and decide which details are most relevant—without dictating a rigid format.

    Args:
        query (str): The user's natural language query.
        user_data: The data retrieved from the database (a User object or a list of User objects).

    Returns:
        str: A clear and organized response as determined by the LLM.
    """
    try:
        parsed_query = parse_user_query(query)

        # Retrieve data dynamically.
        if user_data is None and parsed_query.get("name"):
            user_data = get_user_by_name(parsed_query["name"])

        # Build the context as a raw JSON string for the LLM.
        if user_data is None:
            context = "No user data found matching your query."
        elif isinstance(user_data, list):
            context = json.dumps([user.model_dump() for user in user_data], indent=2)
        else:
            context = json.dumps(user_data.model_dump(), indent=2)

        # Open-ended system prompt:
        system_prompt = """
You are a helpful database assistant. You are provided with a query and raw user data in JSON format (which conforms to the Pydantic User model). 
Analyze the user data, decide which details are most relevant to answer the query, and then produce a clear, organized, and human-friendly response.
Do not simply echo the raw JSON. Instead, format the answer using headings, bullet points, numbered lists, or any structure you deem appropriate.
Keep your answer concise, factual, and professional. Format data based on what you think is the best way to show the data
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Query: {query}\nUser Data:\n{context}"}
        ]
        response = call_groq_api(messages)
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Error generating response: {str(e)}")
        return "I'm sorry, but I encountered an error while processing your request. Please try again later."


def process_user_query(query):
    """
    Process a user query by understanding the query, retrieving data based on it, and generating a response.

    Args:
        query (str): The user's natural language query.

    Returns:
        str: The assistant's response.
    """
    try:
        parsed_query = parse_user_query(query)
        if parsed_query.get("name"):
            user_data = get_user_by_name(parsed_query["name"])
            if user_data is None:
                return f"I couldn't find anyone named {parsed_query['name']} in the database."
        else:
            user_data = get_all_users()
        return generate_response(query, user_data)
    except Exception as e:
        logger.error(f"Error processing user query: {str(e)}")
        return "I'm sorry, but I encountered an error while processing your request. Please try again later."