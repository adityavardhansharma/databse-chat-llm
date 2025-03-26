from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import os
import logging
from models import ChatRequest, ChatResponse
from llm_service import process_user_query

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "default-secret-key")


@app.route("/")
def index():
    """Render the chat interface."""
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    """
    Process a chat request and return a response.

    Expects a JSON payload with a 'query' field.
    Returns a JSON response with a 'response' field and optional 'error' field.
    """
    try:
        # Parse and validate the request
        data = request.json
        chat_request = ChatRequest(query=data.get("query", ""))

        # Process the query
        response_text = process_user_query(chat_request.query)

        # Create and return the response
        chat_response = ChatResponse(response=response_text)
        return jsonify(chat_response.model_dump())

    except Exception as e:
        logger.error(f"Error processing chat request: {str(e)}")
        error_response = ChatResponse(
            response="I'm sorry, but I encountered an error while processing your request.",
            error=str(e)
        )
        return jsonify(error_response.model_dump()), 500


if __name__ == "__main__":
    app.run(debug=True)
