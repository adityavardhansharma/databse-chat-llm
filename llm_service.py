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
        "model": "llama-3.3-70b-versatile",
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
    Use Groq's Gemma model to understand the user's intent and extract relevant information.

    Args:
        query (str): The user's natural language query.

    Returns:
        dict: A dictionary containing the parsed intent and parameters.
    """
    try:
        system_prompt = """
        You are a precise query parser for a user database. Extract ONLY the explicitly mentioned search criteria.

        The database has a table with fields: id, name, age, gender, phone_no, pincode, address.

        Return a JSON object with these fields:
        {
            "name": string or null (specific name if searching for an individual),
            "location": string or null (exact location mentioned, e.g., "Jammu"),
            "min_age": number or null (minimum age if specified),
            "max_age": number or null (maximum age if specified),
            "fields_requested": ["list", "of", "requested", "fields"],
            "is_all_info": true/false (whether all information is requested)
        }

        Be literal - only include criteria explicitly stated in the query.
        Do not infer or assume additional criteria.
        Your response must be valid JSON only, with no additional text.
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]

        response = call_groq_api(messages)

        # Extract the content from the response
        parsed_intent_text = response["choices"][0]["message"]["content"]
        logger.info(f"Raw parsed intent: {parsed_intent_text}")

        # Extract JSON from the response
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
    Generate a natural language response based on the user's query and retrieved data.

    Args:
        query (str): The user's natural language query.
        user_data: The data retrieved from the database (a User object or list of User objects).

    Returns:
        str: A natural language response.
    """
    try:
        # Parse the query to understand intent
        parsed_query = parse_user_query(query)

        # Fetch data if not provided and if a name is found
        if user_data is None and parsed_query.get("name"):
            user_data = get_user_by_name(parsed_query["name"])

        # Prepare the context string
        if user_data is None:
            context = "No user data found matching the query."
        elif isinstance(user_data, list):
            context = f"Found {len(user_data)} users matching the query."
            # Include all users in the context
            for i, user in enumerate(user_data):
                context += f"\nUser {i + 1}: {user.model_dump_json()}"
        else:
            context = f"User data: {user_data.model_dump_json()}"

        system_prompt = """
        You are a database assistant providing search results to users.

        Follow these rules strictly:
        1. Be concise and direct - no unnecessary explanations
        2. Format the response clearly with numbered results if multiple users found
        3. Only mention the information that was requested
        4. Do not mention the database structure or implementation details
        5. Do not add commentary about the search process
        6. Present only factual information from the results
        7. Use a professional, neutral tone

        For multiple results, use this format:
        "Found X users matching your criteria:
        1. [Name]: [relevant details]
        2. [Name]: [relevant details]"

        For a single result, use this format:
        "[Name]: [relevant details]"

        When showing age-related results, be precise and factual without unnecessary commentary.
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Query: {query}\nContext: {context}"}
        ]

        response = call_groq_api(messages)
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Error generating response: {str(e)}")
        return "I'm sorry, but I encountered an error while processing your request. Please try again later."


def process_user_query(query):
    """
    Process a user query by understanding intent, retrieving data, and generating a response.

    Args:
        query (str): The user's natural language query.

    Returns:
        str: A natural language response.
    """
    try:
        parsed_query = parse_user_query(query)

        # Retrieve data based on parsed query
        if parsed_query.get("name"):
            user_data = get_user_by_name(parsed_query["name"])
            if user_data is None:
                return f"I couldn't find anyone named {parsed_query['name']} in the database."
        else:
            # If no specific name is given, return all users (or use criteria with search_users)
            user_data = get_all_users()

        # Generate and return the response
        return generate_response(query, user_data)
    except Exception as e:
        logger.error(f"Error processing user query: {str(e)}")
        return "I'm sorry, but I encountered an error while processing your request. Please try again later."
