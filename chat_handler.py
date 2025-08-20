import logging
from model_inference import generate_response, retriever
from preprocess_input import detect_language, translate_urdu_to_english, translate_to_urdu
from utils.event_utils import (
    load_events,
    search_events,
    get_today_events,
    get_tomorrow_events,
    get_this_week_events,
    get_next_week_events,
    get_next_month_events,
    get_next_seven_days_events,
    format_events
)
from utils.schedule_utils import (
    load_schedule,
    get_course_schedule,
    get_all_schedule
)
from utils.common_utils import extract_keywords
from utils.recommendation_utils import generate_recommendations
from utils.history_utils import append_chat_history  
from utils.suggested_qna import suggested_qna
from datetime import datetime
import re

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def chatbot_reply(user_input, email='default_user@gmail.com', session_id=None):
    logger.debug(f"Received user input: {user_input}")

    # Step 1: Detect Language
    try:
        lang = detect_language(user_input)
        logger.debug(f"Detected language: {lang}")
    except Exception as e:
        logger.error(f"Language detection error: {e}")
        return "Error detecting language."

    # Step 2: Translate Urdu to English
    try:
        translated_input = translate_urdu_to_english(user_input) if lang == "urdu" else user_input
        logger.debug(f"Translated input: {translated_input}")
    except Exception as e:
        logger.error(f"Translation error: {e}")
        return "Error translating input."

    corrected_input = translated_input
    logger.debug(f"Corrected input: {corrected_input}")

    # Step 3: Check for general event type questions
    lower_input = corrected_input.lower()
    general_event_keywords = [
        "what type of events", "what kind of events", "which events occur", 
        "types of events", "kind of events", "what events happen", 
        "what seminars", "what workshops", "what sessions",
        "کس قسم کے ایونٹس", "کوروٹ میں کون سے ایونٹس", "ایونٹس کی اقسام"
    ]
    is_general_event_query = (
        any(phrase in lower_input for phrase in general_event_keywords) or
        ("events" in lower_input and "corvit" in lower_input and 
         not any(time_keyword in lower_input for time_keyword in [
             "today", "tomorrow", "this week", "next week", "this month", "next month",
             "آج", "کل", "اس ہفتے", "اگلے ہفتے", "اس مہینے", "اگلے مہینے"
         ]))
    )

    if is_general_event_query:
        logger.debug("Detected general event type question.")
        question = (
            "What types of events occur at Corvit?" if lang == "english" else 
            "کوروٹ میں کس قسم کے ایونٹس ہوتے ہیں؟"
        )
        response = suggested_qna.get(
            question, 
            "Corvit hosts various events like workshops, seminars, and webinars."
        )
        append_chat_history(email, corrected_input, response, session_id=session_id)
        return response

    # Step 4: Recommendation-related logic
    if any(kw in lower_input for kw in ["recommend", "suggest", "what should i learn", "what do you recommend", "which course is good", "which course should i take"]):
        logger.debug("Processing recommendation query.")
        try:
            logger.debug(f"Processing recommendations for email: {email}")
            recommendations = generate_recommendations(email, session_id=session_id)
            logger.debug(f"Generated recommendations: {recommendations}")

            if recommendations:
                response_text = "**Based on your interests, we recommend:**\n\n" + recommendations
                append_chat_history(email, corrected_input, response_text, session_id=session_id)
                return translate_to_urdu(response_text) if lang == "urdu" else response_text
            else:
                fallback = "Sorry, we couldn't generate any recommendations at the moment. Try asking about a topic you're interested in!"
                append_chat_history(email, corrected_input, fallback, session_id=session_id)
                return translate_to_urdu(fallback) if lang == "urdu" else fallback
        except Exception as e:
            logger.error(f"Recommendation error for {email}: {str(e)}", exc_info=True)
            error_msg = "Error generating recommendations. Please try again or contact support."
            append_chat_history(email, corrected_input, error_msg, session_id=session_id)
            return translate_to_urdu(error_msg) if lang == "urdu" else error_msg

    # Step 5: Event-related Logic
    event_keywords = ["event", "seminar", "webinar", "orientation", "workshop", "meetup"]
    if any(word in lower_input for word in event_keywords):
        logger.debug("Processing event-related query.")
        try:
            events = load_events()
            logger.debug(f"Loaded events: {events}")
            filtered = []

            if "today" in lower_input:
                filtered = get_today_events(events)
                logger.debug("Filtered for today’s events.")
            elif "tomorrow" in lower_input:
                filtered = get_tomorrow_events(events)
                logger.debug("Filtered for tomorrow’s events.")
            elif "this week" in lower_input:
                filtered = get_this_week_events(events)
                logger.debug("Filtered for this week’s events.")
            elif "next week" in lower_input:
                filtered = get_next_week_events(events)
                logger.debug("Filtered for next week’s events.")
            elif "next month" in lower_input:
                filtered = get_next_month_events(events)
                logger.debug("Filtered for next month’s events.")
            else:
                filtered = search_events(corrected_input, events)
                logger.debug("Filtered by search.")

            if filtered:
                combined = "\n\n---\n\n".join(format_events(filtered))
                logger.debug(f"Event response: {combined}")
                append_chat_history(email, corrected_input, combined, session_id=session_id)
                return translate_to_urdu(combined) if lang == "urdu" else combined
            else:
                fallback = (
                    "Sorry, I couldn't find any relevant event info.\n"
                    "For more information:\n\n"
                    "Contact Corvit: 051-111-333-222\n"
                    "Email: info@corvit.com.pk\n"
                    "Website: https://www.corvit.com.pk"
                )
                logger.debug(f"Event fallback response: {fallback}")
                append_chat_history(email, corrected_input, fallback, session_id=session_id)
                return translate_to_urdu(fallback) if lang == "urdu" else fallback
        except Exception as e:
            logger.error(f"Event processing error: {e}")
            error_msg = "Error processing event query."
            append_chat_history(email, corrected_input, error_msg, session_id=session_id)
            return translate_to_urdu(error_msg) if lang == "urdu" else error_msg

    # Step 6: Schedule/class timing logic
    schedule_keywords = ["timing", "class", "schedule", "classes", "Course"]
    if any(kw in lower_input for kw in ["class timing", "class schedule", "timing", "schedule", "class timings", "classes timing", "timing of"]):
        logger.debug("Processing schedule-related query.")
        try:
            schedule_data = load_schedule()
            logger.debug(f"Loaded schedule: {schedule_data}")
            all_course_names = [entry["course"].lower() for entry in schedule_data]
            keywords = extract_keywords(corrected_input)
            logger.debug(f"Extracted keywords: {keywords}")

            filtered_keywords = [
                kw for kw in keywords
                if any(kw.lower() in course for course in all_course_names)
            ]
            logger.debug(f"Filtered keywords: {filtered_keywords}")

            if filtered_keywords:
                matched_courses = []
                for kw in filtered_keywords:
                    course_result = get_course_schedule(kw, schedule_data)
                    if course_result:
                        matched_courses.extend(course_result)
                        logger.debug(f"Matched courses for {kw}: {course_result}")

                if matched_courses:
                    combined = "\n\n---\n\n".join(matched_courses)
                    logger.debug(f"Schedule response: {combined}")
                    append_chat_history(email, corrected_input, combined, session_id=session_id)
                    return translate_to_urdu(combined) if lang == "urdu" else combined
                else:
                    fallback = (
                        "Sorry, currently this course is not available.\n"
                        "For more information:\n\n"
                        "Contact Corvit: 051-111-333-222\n"
                        "Email: info@corvit.com.pk\n"
                        "Website: https://www.corvit.com.pk"
                    )
                    logger.debug(f"Schedule fallback response: {fallback}")
                    append_chat_history(email, corrected_input, fallback, session_id=session_id)
                    return translate_to_urdu(fallback) if lang == "urdu" else fallback
            else:
                result = get_all_schedule(schedule_data)
                logger.debug(f"Full schedule: {result}")
                combined = "\n\n---\n\n".join(result)
                append_chat_history(email, corrected_input, combined, session_id=session_id)
                return translate_to_urdu(combined) if lang == "urdu" else combined
        except Exception as e:
            logger.error(f"Schedule processing error: {e}")
            error_msg = "Error processing schedule query."
            append_chat_history(email, corrected_input, error_msg, session_id=session_id)
            return translate_to_urdu(error_msg) if lang == "urdu" else error_msg

    # Step 7: Check suggested_qna for other predefined responses
    if corrected_input in suggested_qna:
        logger.debug(f"Found response in suggested_qna for: {corrected_input}")
        response = suggested_qna[corrected_input]
        append_chat_history(email, corrected_input, response, session_id=session_id)
        return response

    # Step 8: General response using generate_response
    logger.debug("Falling back to generate_response.")
    try:
        english_response = generate_response(corrected_input)
        logger.debug(f"Generated response: {english_response}")
        if not english_response:
            english_response = (
                "Sorry, I couldn't understand your question. Please contact Corvit at 051-111-333-222 or email info@corvit.com.pk"
            )
            logger.debug(f"Fallback response: {english_response}")
        final_response = translate_to_urdu(english_response) if lang == "urdu" else english_response
        logger.debug(f"Final response: {final_response}")
        append_chat_history(email, corrected_input, final_response, session_id=session_id)
        return final_response
    except Exception as e:
        logger.error(f"Generate response error: {e}")
        error_msg = "Error generating response."
        append_chat_history(email, corrected_input, error_msg, session_id=session_id)
        return translate_to_urdu(error_msg) if lang == "urdu" else error_msg