import json
from utils.common_utils import extract_keywords

def load_schedule():
    try:
        with open("data/schedule.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def format_schedule(entry):
    return (
        f"Course: {entry['course']}\n"
        f"Instructor: {entry['instructor']}\n"
        f"Days: {entry['days']}\n"
        f"Time: {entry['time']}\n"
        f"Start Date: {entry['starting_date']}\n"
        f"Mode: {entry['mode']}\n"
        f"City: {entry['city']}"
    )

# ✅ New: For specific course schedule
def get_course_schedule(course_name, schedule):
    course_name = course_name.lower()
    for entry in schedule:
        if course_name in entry.get("course", "").lower():
            return [format_schedule(entry)]
    return []

# ✅ New: For full schedule
def get_all_schedule(schedule):
    return [format_schedule(entry) for entry in schedule]

# (Optional) Old search function — useful for fallback or general search
def search_schedule(user_input, schedule):
    keywords = extract_keywords(user_input)
    results = []

    # If a specific course is mentioned
    for entry in schedule:
        course = entry.get("course", "").lower()
        if any(kw in course for kw in keywords):
            results.append(format_schedule(entry))

    # If nothing matched but query is about general schedule
    if not results and any(word in user_input.lower() for word in ["schedule", "class", "classes", "timing"]):
        for entry in schedule:
            results.append(format_schedule(entry))

    return results
