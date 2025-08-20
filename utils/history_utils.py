import os
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(filename='chatbot_errors.log', level=logging.DEBUG)

HISTORY_DIR = "chat_logs"

# Ensure the directory exists
os.makedirs(HISTORY_DIR, exist_ok=True)

def sanitize_filename(email):
    """
    Sanitize email address for use as a filename (e.g., rehab11@gamil.com -> rehab11_gamil_com.json).
    """
    if not email or not isinstance(email, str):
        return None
    # Replace special characters with underscores and ensure .json extension
    sanitized = email.replace('@', '_').replace('.', '_') + '.json'
    return sanitized

def load_user_chat_history(email, session_id=None):
    """
    Load the latest three user messages from the specified session or all sessions if session_id is None.
    """
    if not email or not isinstance(email, str):
        logging.error(f"Invalid email: {email}")
        return []
    
    filename = sanitize_filename(email)
    if not filename:
        logging.error(f"Failed to sanitize email: {email}")
        return []
    
    filepath = os.path.join(HISTORY_DIR, filename)
    logging.debug(f"Attempting to load chat history from {filepath}")
    
    if not os.path.exists(filepath):
        logging.debug(f"No chat history file found for {email} at {filepath}")
        return []
    
    try:
        with open(filepath, "r", encoding="utf-8") as file:
            chat_sessions = json.load(file)
        
        if not isinstance(chat_sessions, list):
            logging.error(f"Invalid chat history format for {email}: expected list, got {type(chat_sessions)}")
            return []
        
        user_messages = []
        if session_id:
            # Find the session with the matching session_id
            for session in chat_sessions:
                if session.get("title") == session_id and isinstance(session.get("messages"), list):
                    # Extract the latest three user messages from this session
                    session_messages = [
                        {"user_message": msg["text"]}
                        for msg in session["messages"]
                        if msg.get("role") == "user" and "text" in msg and msg["text"].strip()
                    ]
                    user_messages = session_messages[-3:]  # Take the latest 3
                    break
        else:
            # Fallback: Extract latest three user messages from all sessions
            chat_sessions = sorted(chat_sessions, key=lambda x: x.get("title", ""), reverse=True)
            for session in chat_sessions:
                if isinstance(session, dict) and "messages" in session and isinstance(session["messages"], list):
                    for message in session["messages"]:
                        if message.get("role") == "user" and "text" in message and message["text"].strip():
                            user_messages.append({"user_message": message["text"]})
            user_messages = user_messages[-3:]  # Take the latest 3
        
        logging.debug(f"Extracted {len(user_messages)} user messages for {email} (session_id: {session_id}): {user_messages}")
        return user_messages
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON in {filepath}: {str(e)}")
        return []
    except Exception as e:
        logging.error(f"Error loading chat history for {email}: {str(e)}", exc_info=True)
        return []

def append_chat_history(email, user_msg, bot_response, session_id=None):
    """
    Append a user and bot message pair to the chat_logs/{email}.json file in the specified session.
    """
    if not email or not isinstance(email, str):
        logging.error(f"Invalid email for appending history: {email}")
        return
    
    filename = sanitize_filename(email)
    if not filename:
        logging.error(f"Failed to sanitize email: {email}")
        return
    
    filepath = os.path.join(HISTORY_DIR, filename)
    logging.debug(f"Appending chat history to {filepath}")
    
    chat_sessions = load_raw_chat_history(filepath)
    
    # Find or create the session
    current_session = None
    if session_id:
        for session in chat_sessions:
            if session.get("title") == session_id:
                current_session = session
                break
    if not current_session:
        current_session = {"title": session_id or f"Chat {datetime.now().strftime('%d-%b %H:%M')}", "messages": []}
        chat_sessions.append(current_session)
    
    # Append new messages if they are non-empty
    if user_msg and isinstance(user_msg, str):
        current_session["messages"].append({
            "role": "user",
            "text": user_msg.strip()
        })
        logging.debug(f"Appended user message for {email}: {user_msg.strip()}")
    if bot_response and isinstance(bot_response, str):
        current_session["messages"].append({
            "role": "bot",
            "text": bot_response.strip()
        })
        logging.debug(f"Appended bot response for {email}: {bot_response.strip()}")
    
    # Save updated history
    try:
        with open(filepath, "w", encoding="utf-8") as file:
            json.dump(chat_sessions, file, indent=4, ensure_ascii=False)
        logging.debug(f"Successfully appended chat history for {email} to {filepath}")
    except Exception as e:
        logging.error(f"Error saving chat history for {email}: {str(e)}", exc_info=True)

def load_raw_chat_history(filepath):
    """
    Helper function to load raw chat history or return an empty list.
    """
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as file:
                data = json.load(file)
                logging.debug(f"Loaded raw chat history from {filepath}: {len(data)} sessions")
                return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            logging.error(f"Invalid JSON in {filepath}")
            return []
    logging.debug(f"No chat history file found at {filepath}")
    return []