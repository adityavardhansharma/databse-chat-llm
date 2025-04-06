import os
import json
import logging
from dotenv import load_dotenv
from database import get_user_by_name, get_all_users
from groq import Groq

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Groq API credentials
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    logger.error("Groq API key not found in environment variables")
    raise ValueError("Groq API key not found in environment variables")

# Initialize Groq client
client = Groq(api_key=GROQ_API_KEY)

MODEL_NAME = "meta-llama/llama-4-scout-17b-16e-instruct"


def call_groq_api(messages, response_format=None):
    """
    Call the Groq API with the given messages.

    Args:
        messages (list): List of message dicts with 'role' and 'content'.
        response_format (dict, optional): Format specification for the response.

    Returns:
        The API response object.
    """
    try:
        params = {
            "model": MODEL_NAME,
            "messages": messages
        }
        if response_format:
            params["response_format"] = response_format

        response = client.chat.completions.create(**params)
        return response
    except Exception as e:
        logger.error(f"Error calling Groq API: {str(e)}")
        raise


def parse_user_query(query):
    """
    Use Llama to extract explicit search criteria from the user's query.

    Args:
        query (str): The user's natural language query.

    Returns:
        dict: Parsed intent and parameters.
    """
    try:
        system_prompt = """
You are a specialized database query parser with one task: extract ONLY explicitly mentioned search criteria.

Database schema: id, name, age, gender, phone_no, pincode, address

OUTPUT REQUIREMENTS:
- Return ONLY valid JSON with these exact keys:
{
  "name": string or null,
  "location": string or null,
  "min_age": number or null,
  "max_age": number or null,
  "fields_requested": ["field1", "field2"],
  "is_all_info": boolean
}

STRICT RULES:
1. Include ONLY criteria explicitly stated in the query
2. For age ranges: "over 30" → min_age=31, "under 40" → max_age=39
3. For location, extract city, state, pincode or any location identifier
4. Set is_all_info=true only if query asks for "all information" or "everything"
5. fields_requested should contain specific fields mentioned (name, age, etc.)
6. DO NOT add explanations or text outside the JSON
7. DO NOT infer criteria not directly mentioned
8. If a field isn't mentioned, set it to null

RESPONSE FORMAT: Valid JSON object only, no preamble or explanation.
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]

        response_format = {"type": "json_object"}
        response = call_groq_api(messages, response_format)

        parsed_text = response.choices[0].message.content
        logger.info(f"Raw parsed intent: {parsed_text}")

        try:
            parsed_intent = json.loads(parsed_text)
        except json.JSONDecodeError:
            import re
            match = re.search(r'({.*})', parsed_text, re.DOTALL)
            if match:
                parsed_intent = json.loads(match.group(1))
            else:
                raise ValueError("Could not extract valid JSON from LLM response")

        logger.info(f"Parsed intent: {parsed_intent}")
        return parsed_intent

    except Exception as e:
        logger.error(f"Error parsing user query: {str(e)}")
        raise


def generate_response(query, user_data=None):
    """
    Generate a natural language response based on the query and retrieved data.

    Args:
        query (str): User's query.
        user_data: Retrieved user data (User object or list).

    Returns:
        str: Formatted response.
    """
    try:
        parsed_query = parse_user_query(query)

        if user_data is None and parsed_query.get("name"):
            user_data = get_user_by_name(parsed_query["name"])

        if user_data is None:
            context = "No user data found matching your query."
        elif isinstance(user_data, list):
            context = json.dumps(
                [user.model_dump() for user in user_data], indent=2
            )
        else:
            context = json.dumps(user_data.model_dump(), indent=2)

        system_prompt = """
You are an expert database assistant presenting user information. Your goal is to transform raw data into clear, concise, and well-structured responses.

CONTEXT:
- You're working with a user database containing: id, name, age, gender, phone_no, pincode, address
- You'll receive a user query and JSON data from the database
- The user wants specific information presented in a readable format

RESPONSE GUIDELINES:
1. ANALYZE the query to understand what information is being requested
2. FOCUS on the specific data points relevant to the query
3. STRUCTURE your response with appropriate formatting:
   - Use headings for different users or data categories
   - Use bullet points for listing multiple attributes
   - Use tables for comparing multiple users (if applicable)
4. HIGHLIGHT key information that directly answers the query
5. SUMMARIZE when dealing with multiple users (e.g., "Found 5 users matching your criteria")
6. ADAPT your formatting based on the amount and type of data
7. BE CONCISE - avoid unnecessary explanations about the data structure
8. USE NATURAL LANGUAGE - transform field names into readable sentences

TONE: Professional, helpful, and direct. Prioritize clarity and readability.
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Query: {query}\nUser Data:\n{context}"
            }
        ]

        response = call_groq_api(messages)
        return response.choices[0].message.content

    except Exception as e:
        logger.error(f"Error generating response: {str(e)}")
        return "I'm sorry, but I encountered an error while processing your request. Please try again later."


def process_user_query(query):
    """
    Process a user query end-to-end.

    Args:
        query (str): User's query.

    Returns:
        str: Assistant's response.
    """
    try:
        parsed_query = parse_user_query(query)

        if parsed_query.get("name"):
            user_data = get_user_by_name(parsed_query["name"])
            if user_data is None:
                return (
                    f"I couldn't find anyone named {parsed_query['name']} "
                    "in the database."
                )
        else:
            user_data = get_all_users()

        return generate_response(query, user_data)

    except Exception as e:
        logger.error(f"Error processing user query: {str(e)}")
        return "I'm sorry, but I encountered an error while processing your request. Please try again later."
