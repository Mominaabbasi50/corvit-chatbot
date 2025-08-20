import logging
import re
import json
import numpy as np
import os
from utils.history_utils import load_user_chat_history
from sentence_transformers import SentenceTransformer
import faiss

# Configure logging
logging.basicConfig(filename='chatbot_errors.log', level=logging.DEBUG)

# Define the path to the dataset relative to this file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(BASE_DIR, "..", "data", "corvit_dataset_retriever.json")

# Load dataset with UTF-8 encoding
try:
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        dataset = json.load(f)
    logging.info(f"Successfully loaded dataset from {DATASET_PATH}")
except FileNotFoundError:
    logging.error(f"Dataset file not found at {DATASET_PATH}")
    raise FileNotFoundError(
        f"Error: Dataset file '{DATASET_PATH}' not found. Please ensure the file exists in the 'data' folder relative to 'utils'."
    )
except json.JSONDecodeError as e:
    logging.error(f"Invalid JSON format in {DATASET_PATH}: {str(e)}")
    raise json.JSONDecodeError(
        f"Error: Invalid JSON format in dataset file: {str(e)}", e.doc, e.pos
    )
except UnicodeDecodeError as e:
    logging.error(f"Unicode decode error in {DATASET_PATH}: {str(e)}")
    raise UnicodeDecodeError(
        f"Error: Unable to decode dataset file with UTF-8: {str(e)}. Try checking the file's encoding.",
        e.encoding, e.object, e.start, e.end
    )

# Initialize sentence transformer and FAISS index
embedder = SentenceTransformer('all-MiniLM-L6-v2')
dimension = 384  # Sentence transformer embedding size
faiss_index = faiss.IndexFlatL2(dimension)
page_contents = [entry["page_content"] for entry in dataset]
embeddings = embedder.encode(page_contents, convert_to_numpy=True)
faiss_index.add(embeddings)


# Define intent categories with keywords
INTENT_CATEGORIES = {
    "networking": ["ccna", "ccnp", "network", "networking", "cisco", "vlan", "ospf", "eigrp"],
    "cybersecurity": ["cybersecurity", "security", "ethical hacking", "ceh"],
    "programming": ["python", "programming", "code", "coding", "scripting", "web development", "flask", "django"],
    "ai": ["ai", "machine learning", "artificial intelligence", "deep learning", "tensorflow", "pytorch"],
    "career": ["job", "career", "certification", "employment", "internship", "portfolio"],
    "enrollment": ["enroll", "register", "admission", "fees", "documents"],
    "instructor": ["instructor", "teacher", "who teaches"],
    "location_contact": ["location", "contact", "islamabad", "branch"],
}

def categorize_query(query):
    """
    Categorize a query based on keywords or semantic similarity to dataset.
    """
    query = query.lower().strip()
    for category, keywords in INTENT_CATEGORIES.items():
        if any(kw in query for kw in keywords):
            return category
    
    # Fallback to semantic similarity
    query_embedding = embedder.encode([query])[0]
    distances, indices = faiss_index.search(np.array([query_embedding]), k=1)
    if distances[0][0] < 0.35:  # Similarity threshold
        closest_query = dataset[indices[0][0]]["page_content"].lower()
        for category, keywords in INTENT_CATEGORIES.items():
            if any(kw in closest_query for kw in keywords):
                return category
    return "general"

def generate_recommendations(email, session_id=None):
    """
    Generate learning recommendations based on the latest three user messages in the current session,
    tailored to Corvit Systems Islamabad's offerings using the dataset.

    Args:
        email (str): The user's email to load chat history for (e.g., 'user@gamil.com').
        session_id (str, optional): The session ID to filter messages.

    Returns:
        str: A recommendation message tailored to Corvit Systems Islamabad or an error message.
    """
    try:
        if not email or not isinstance(email, str):
            logging.error(f"Invalid email: {email}")
            return (
                "Error: Invalid email provided. Please provide a valid email to get personalized recommendations "
                "from Corvit Systems Islamabad. Contact us at 0303-8888555 or visit https://corvit.com."
            )

        history = load_user_chat_history(email, session_id=session_id)
        logging.debug(f"Loaded history for {email} (session_id: {session_id}): {history}")
        
        if not history:
            logging.info(f"No chat history found for {email} in session {session_id}")
            return (
                "I don’t have enough information from your recent questions to recommend anything yet. "
                "Corvit Systems Islamabad offers top IT courses like CCNA, Cybersecurity, and Artificial Intelligence, taught by 8 CCIE instructors. "
                "Visit our campus at 70-W, Al-Malik Center, Jinnah Avenue, call 0303-8888555, or check https://corvit.com to start your IT journey!"
            )

        # Use the latest three messages
        recent_messages = [item["user_message"].lower() for item in history[-3:]]
        logging.debug(f"Raw recent messages for {email}: {recent_messages}")

        # Normalize text
        joined = " ".join(re.sub(r'[^\w\s]', '', msg.strip()).replace("  ", " ") for msg in recent_messages if msg.strip())
        logging.debug(f"Joined and normalized text for {email}: '{joined}'")

        # Categorize queries
        categories = [categorize_query(msg) for msg in recent_messages]
        dominant_category = max(set(categories), key=categories.count, default="general")
        logging.debug(f"Dominant category for {email}: {dominant_category}")

        # Retrieve dataset context for the latest query
        latest_query = recent_messages[-1] if recent_messages else ""
        query_embedding = embedder.encode([latest_query])[0]
        distances, indices = faiss_index.search(np.array([query_embedding]), k=1)
        dataset_answer = ""
        if distances[0][0] < 0.35:  # Similarity threshold
            dataset_answer = dataset[indices[0][0]]["metadata"]["answer"]
            logging.debug(f"Dataset answer for {email}: {dataset_answer}")

        # Generate recommendations based on dominant category
        if dominant_category == "networking":
            return (
                f"{dataset_answer or 'Based on your interest in networking,'} Corvit Systems Islamabad’s CCNA course, covering VLANs, OSPF, and automation, is perfect for you, taught by experts like Mr. Abdul Waheed (3xCCIE). "
                "Consider our CCNP or Network Automation with Python courses to advance your skills. "
                "Visit 70-W, Al-Malik Center, Jinnah Avenue, call 0303-8888555, or check https://corvit.com for details."
            )
        elif dominant_category == "cybersecurity":
            return (
                f"{dataset_answer or 'Your interest in cybersecurity is a great fit for'} Corvit Systems Islamabad’s Cybersecurity course, covering ethical hacking and network security. "
                "You might also explore our Certified Ethical Hacker (CEH) training to boost your credentials. "
                "Contact our Islamabad campus at 70-W, Al-Malik Center, Jinnah Avenue, at 0303-8888555 or visit https://corvit.com."
            )
        elif dominant_category == "programming":
            return (
                f"{dataset_answer or 'Since you’re interested in programming,'} Corvit Systems Islamabad offers a Web Development course with Flask and Django, ideal for building modern applications. "
                "You could also explore Python for Data Science to diversify your skills. "
                "Reach out at 70-W, Al-Malik Center, Jinnah Avenue, via 0303-8888555 or https://corvit.com for enrollment details."
            )
        elif dominant_category == "ai":
            return (
                f"{dataset_answer or 'Your interest in AI aligns with'} Corvit Systems Islamabad’s Artificial Intelligence course, covering machine learning and TensorFlow. "
                "Consider our Data Science course to master AI-driven analytics. "
                "Visit our campus at 70-W, Al-Malik Center, Jinnah Avenue, or call 0303-8888555 to get started at https://corvit.com."
            )
        elif dominant_category == "career":
            return (
                f"{dataset_answer or 'To boost your career,'} Corvit Systems Islamabad offers job-oriented certifications like CCNA, AWS, and Full Stack Development. "
                "Our career counseling and internship programs can help you build a strong portfolio. "
                "Contact us at 70-W, Al-Malik Center, Jinnah Avenue, via 0303-8888555 or visit https://corvit.com."
            )
        elif dominant_category == "enrollment":
            return (
                f"{dataset_answer or 'To enroll at Corvit Systems Islamabad,'} visit https://corvit.com, select a course like CCNA or Cybersecurity, and follow the registration process at our campus, 70-W, Al-Malik Center, Jinnah Avenue. "
                "Our team can guide you on fees and documents. "
                "Call 0303-8888555 or email info@corvit.com for assistance."
            )
        elif dominant_category == "instructor":
            return (
                f"{dataset_answer or 'Corvit Systems Islamabad boasts expert instructors like'} Mr. Abdul Waheed (3xCCIE) for courses like CCNA and CCNP, ensuring top-tier training. "
                "Learn from our team of 8 CCIE professionals to excel in IT. "
                "Visit us at 70-W, Al-Malik Center, Jinnah Avenue, or call 0303-8888555 to explore our courses at https://corvit.com."
            )
        elif dominant_category == "location_contact":
            return (
                f"{dataset_answer or 'Corvit Systems Islamabad is located at'} 70-W, Al-Malik Center, Jinnah Avenue, offering top IT courses like CCNA and Cybersecurity. "
                "Reach out at 0303-8888555 or info@corvit.com for course schedules. "
                "Visit https://corvit.com to explore our offerings."
            )
        else:
            # Handle irrelevant or general queries
            if any(kw in joined for kw in ["cook", "cooking", "travel", "traveling", "gaming", "sad", "hobbies","mood", "joke","dress","art","dresses","animals"]):
                return (
                    "Corvit Systems Islamabad specializes in IT training, offering courses like CCNA, Cybersecurity, and Artificial Intelligence, but we don’t provide training for cooking or travel. "
                    "Explore our industry-recognized programs to build in-demand tech skills. "
                    "Visit our campus at 70-W, Al-Malik Center, Jinnah Avenue, call 0303-8888555, or check https://corvit.com for details."
                )
            return (
                f"{dataset_answer or 'Based on current tech trends,'} I recommend exploring Corvit Systems Islamabad’s popular courses like CCNA, Cybersecurity, or Artificial Intelligence to build in-demand IT skills. "
                "Our hands-on training and 8 CCIE instructors ensure you’re job-ready. "
                "Visit our campus at 70-W, Al-Malik Center, Jinnah Avenue, call 0303-8888555, or check https://corvit.com for details."
            )
    
    except Exception as e:
        logging.error(f"Error generating recommendations for {email}: {str(e)}", exc_info=True)
        return (
            "Error: Unable to generate recommendations due to an internal issue. "
            "Please try asking about Corvit Systems Islamabad’s IT courses, such as CCNA or Cybersecurity. "
            "Contact us at 70-W, Al-Malik Center, Jinnah Avenue, via 0303-8888555 or https://corvit.com."
        )