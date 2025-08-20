import streamlit as st
from auth import init_user_db, register_user, login_user
from utils.event_utils import load_events, get_next_seven_days_events
from utils.chat_utils import load_user_chats, save_user_chats, delete_chat
from chat_handler import chatbot_reply
from preprocess_input import detect_language, translate_urdu_to_english
from datetime import datetime
import streamlit.components.v1 as components
from PIL import Image
from utils.suggested_qna import suggested_qna
import os
import re

def is_urdu(text):
    urdu_pattern = re.compile(r'[\u0600-\u06FF]')
    return bool(urdu_pattern.search(text))

def is_english(text):
    english_pattern = re.compile(r'^[A-Za-z0-9\s\.,!?;:\'\"()\[\]\-]+$')
    return bool(english_pattern.match(text.strip()))

# Init user DB
init_user_db()

# Language translations
def get_translations():
    return {
        "english": {
            "greeting": "What can I assist you with today?",
            "good_morning": "Good morning",
            "good_afternoon": "Good afternoon",
            "good_evening": "Good evening",
            "input_placeholder": "Type your question here...",
            "new_chat": "➕ New Chat",
            "logout": "Logout",
            "chats": " Chats",
            "events": "🔔 This Week's Events",
            "reminder_close": "❌ Close Reminder",
            "reminder_show": "🔁 Show Weekly Reminder Again",
            "welcome_message": "Hello! I’m the Corvit Customer Service Assistant. How can I help you today?",
            "suggested_questions": [
                "What is the fee structure of courses?",
                "How can I register for a course?",
                "What are the class timings at Corvit?",
                "Where is the Corvit office located?",
                "What courses does Corvit offer?"
            ]
        },
        "urdu": {
            "greeting": "میں آپ کی کیا مدد کر سکتا ہوں؟",
            "good_morning": "صبح بخیر",
            "good_afternoon": "دوپہر بخیر",
            "good_evening": "شام بخیر",
            "input_placeholder": "اپنا سوال یہاں لکھیں...",
            "new_chat": "➕ نئی گفتگو",
            "logout": "لوگ آؤٹ",
            "chats": " گفتگوئیں",
            "events": "🔔 اس ہفتے کی تقریبات",
            "reminder_close": "❌ بند کریں",
            "reminder_show": "🔁 دوبارہ دکھائیں",
            "welcome_message": "السلام علیکم! میں کوروٹ کا کسٹمر سروس اسسٹنٹ ہوں۔ آپ کی کس طرح مدد کر سکتا ہوں؟",
            "suggested_questions": [
                "کورسز کی فیس کا ڈھانچہ کیا ہے؟",
                "میں کورس کے لیے کیسے رجسٹر کر سکتا ہوں؟",
                "کوروٹ میں کلاسز کے اوقات کیا ہیں؟",
                "کوروٹ آفس کہاں واقع ہے؟",
                "کوروٹ کون سے کورسز آفر کرتا ہے؟"
            ]
        }
    }

# Safe logo loading
if os.path.exists("images/corvit_logo.png"):
    logo = Image.open("images/corvit_logo.png")
    col1, col2, col3 = st.columns([3, 4, 1])
    with col2:
        st.image(logo, width=150)

# Load style
if os.path.exists("css/style.css"):
    with open("css/style.css") as f:
        css = f.read()
        st.markdown(f"<style>{css} html body {{ background-color: #800000 !important; }}</style>", unsafe_allow_html=True)

# Header before login
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    if os.path.exists("html/header.html"):
        with open("html/header.html", "r", encoding="utf-8") as f:
            st.markdown(f.read(), unsafe_allow_html=True)

# Session State defaults
st.session_state.setdefault("logged_in", False)
st.session_state.setdefault("first_login", True)
st.session_state.setdefault("username", "")
st.session_state.setdefault("name", "")
st.session_state.setdefault("selected_chat_title", None)
st.session_state.setdefault("delete_states", {})
st.session_state.setdefault("show_popup", True)
st.session_state.setdefault("lang", "english")

translations = get_translations()
lang_raw = st.session_state.get("lang", "english").lower()
lang = "urdu" if lang_raw in ["ur", "urdu", "ur_pk", "ur-in"] else "english"
if lang not in translations:
    lang = "english"

# LOGIN PAGE
if not st.session_state.logged_in:
    st.markdown("<div class='only-login-area'><div class='login-wrapper'><div class='login-box'>", unsafe_allow_html=True)
    st.markdown("<div class='login-title'>Welcome back</div>", unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["Login", "SignUp"])

    with tab1:
        login_username = st.text_input("Enter Email", key="login_user", label_visibility="collapsed", placeholder="Email address")
        login_password = st.text_input("Password", type="password", key="login_pass", label_visibility="collapsed", placeholder="Password")

        if st.button("LOGIN", use_container_width=True):
            user_name = login_user(login_username, login_password)
            if user_name:
                st.session_state.logged_in = True
                st.session_state.username = login_username
                st.session_state.name = user_name
                st.session_state.first_login = True
                st.success("✅ Login successful!")
                st.rerun()
            else:
                st.error("❌ Invalid Email or password.")

    with tab2:
        new_name = st.text_input("Full Name", key="new_name", label_visibility="collapsed", placeholder="Your name")
        new_username = st.text_input("Create Email", key="new_user", label_visibility="collapsed", placeholder="Email address")
        new_password = st.text_input("Create Password", type="password", key="new_pass", label_visibility="collapsed", placeholder="Password")

        if st.button("SIGN UP", use_container_width=True):
            if new_name and new_username and new_password:
                if register_user(new_username, new_password, new_name):
                    st.success("✅ Registered successfully! Now log in.")
                else:
                    st.error("⚠️ Email already exists.")
            else:
                st.warning("⚠️ Please fill in all fields.")

    st.markdown("</div></div></div>", unsafe_allow_html=True)

# ---------- MAIN APP ----------
else:
    username = st.session_state.username
    user_chats = load_user_chats(username)

    # Welcome message on first login
    if st.session_state.first_login:
        new_title = f"Chat {datetime.now().strftime('%d-%b %H:%M')}"
        welcome_message = {"role": "bot", "text": translations[lang]["welcome_message"]}
        user_chats.insert(0, {"title": new_title, "messages": [welcome_message]})
        save_user_chats(username, user_chats)
        st.session_state.selected_chat_title = new_title
        st.session_state.first_login = False

    # Select default chat
    if not st.session_state.selected_chat_title:
        st.session_state.selected_chat_title = user_chats[0]["title"] if user_chats else None

    # -------------------- SIDEBAR --------------------
    with st.sidebar:
        st.markdown("## Corvit Chatbot")

        # 👤 Username & Logout
        # ⚙ Settings Menu with Email > Logout
        if "show_settings_menu" not in st.session_state:
            st.session_state.show_settings_menu = False
        if "show_email_logout" not in st.session_state:
            st.session_state.show_email_logout = False

        # Settings button with expander for email and logout
        with st.expander("⚙ Settings", expanded=st.session_state.show_settings_menu):
            if st.button(f" {username}", key="email_button"):
                st.session_state.show_email_logout = not st.session_state.show_email_logout
            if st.session_state.show_email_logout:
                if st.button(" Logout"):
                    st.session_state.logged_in = False
                    st.session_state.username = ""
                    st.session_state.selected_chat_title = None
                    st.rerun()

        # 🌐 Language Selection 
        with st.expander("🌐 Language", expanded=False):
            lang_selected = st.radio("Select Language", ["English", "اردو"], index=0 if lang == "english" else 1, label_visibility="collapsed")
            new_lang = "english" if lang_selected == "English" else "urdu"
            if new_lang != st.session_state.lang:
                st.session_state.lang = new_lang
                # Update welcome message in current chat
                selected_chat = st.session_state.get("selected_chat_title")
                if selected_chat:
                    for chat in user_chats:
                        if chat["title"] == selected_chat and chat["messages"]:
                            if chat["messages"][0]["role"] == "bot":
                                chat["messages"][0]["text"] = translations[new_lang]["welcome_message"]
                                save_user_chats(username, user_chats)
                                break
                st.rerun()

        st.markdown("---")

        # New Chat button (always visible)
        if st.button(translations[lang].get("new_chat", "New Chat")):
            new_title = f"Chat {datetime.now().strftime('%d-%b %H:%M')}"
            welcome_message = {"role": "bot", "text": translations[lang]["welcome_message"]}
            user_chats.insert(0, {"title": new_title, "messages": [welcome_message]})
            save_user_chats(username, user_chats)
            st.session_state.selected_chat_title = new_title
            st.rerun()

        # Chats list (always visible)
        st.markdown(f"### {translations[lang]['chats']}")
        for i, chat in enumerate(user_chats):
            chat_key = chat["title"]
            cols = st.columns([0.8, 0.2])
            if cols[0].button(f" {chat_key}", key=f"chat_{chat_key}_{i}"):
                st.session_state.selected_chat_title = chat_key
                st.rerun()
            if cols[1].button("⋮", key=f"dots_{chat_key}_{i}", help="chat-options"):
                st.session_state.delete_states[chat_key] = not st.session_state.delete_states.get(chat_key, False)
                st.rerun()
            if st.session_state.delete_states.get(chat_key, False):
                if st.button(f" Delete '{chat_key}'", key=f"delete_{chat_key}_{i}"):
                    delete_chat(username, chat_key)
                    del st.session_state.delete_states[chat_key]
                    if st.session_state.get("selected_chat_title") == chat_key:
                        st.session_state.selected_chat_title = None
                    st.rerun()

        # Events section 
        st.markdown(f"### {translations[lang]['events']}")
        all_events = load_events()
        week_events = get_next_seven_days_events(all_events)
        if week_events and st.session_state.show_popup:
            for e in week_events:
                if st.button(f" {e['title']} ({e['date']})", key=f"event_{e['title']}"):
                    auto_msg = f"** {e['title']}**\n {e['description']}\n {e['date']}"
                    selected_chat = st.session_state.selected_chat_title
                    if selected_chat:
                        current_chat = next(c for c in user_chats if c["title"] == selected_chat)
                        current_chat["messages"].append({"role": "bot", "text": auto_msg})
                        save_user_chats(username, user_chats)
                        st.rerun()
            if st.button(translations[lang]["reminder_close"], key="close_reminder"):
                st.session_state.show_popup = False
                st.rerun()
        elif not st.session_state.show_popup:
            if st.button(translations[lang]["reminder_show"]):
                st.session_state.show_popup = True
                st.rerun()

    # Chat Panel
    selected_chat = st.session_state.selected_chat_title
    if selected_chat:
        current_chat = next(chat for chat in user_chats if chat["title"] == selected_chat)

        with st.container():
            current_hour = datetime.now().hour
            if current_hour < 12:
                greeting = translations[lang]["good_morning"]
            elif current_hour < 17:
                greeting = translations[lang]["good_afternoon"]
            else:
                greeting = translations[lang]["good_evening"]

            st.markdown(f"""
                <div style='text-align: center; margin-top: 80px;'>
                    <h1>{greeting}, {st.session_state.get('name', username)}</h1>
                    <h3>{translations[lang]['greeting']}</h3>
                </div>
            """, unsafe_allow_html=True)

            suggested_questions = translations[lang]["suggested_questions"]

            cols = st.columns(len(suggested_questions))
            for i, question in enumerate(suggested_questions):
                if cols[i].button(question, key=f"suggested_{i}"):
                    current_chat = next(c for c in user_chats if c["title"] == selected_chat)
                    current_chat["messages"].append({"role": "user", "text": question})
                    answer = suggested_qna.get(question, "Sorry, I don't have an answer for that.")
                    current_chat["messages"].append({"role": "bot", "text": answer})
                    save_user_chats(username, user_chats)
                    st.rerun()

        for msg in current_chat["messages"]:
            if msg["role"] == "user":
                st.markdown(f"<div class='chat-bubble-user'><strong> You:</strong> {msg['text']}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='chat-bubble-bot'><strong> Bot:</strong> {msg['text']}</div>", unsafe_allow_html=True)

        # Invisible div to scroll to
        st.markdown("<div id='chat-end'></div>", unsafe_allow_html=True)

        # Scroll to it using JS
        components.html("""
<script>
    setTimeout(() => {
        const el = document.getElementById("chat-end");
        if (el) {
            el.scrollIntoView({ behavior: 'smooth' });
        }
    }, 100);
</script>
""", height=0)

        user_input = st.chat_input(translations[lang]["input_placeholder"])
        if user_input:
            if lang == "urdu" and not is_urdu(user_input):
                st.warning("براہ کرم صرف اردو زبان میں پیغام لکھیں۔")
            elif lang == "english" and not is_english(user_input):
                st.warning("Please type your message in English only.")
            else:
                # Preprocess input for chatbot_reply
                try:
                    lang_detected = detect_language(user_input)
                    corrected_input = translate_urdu_to_english(user_input) if lang_detected == "urdu" else user_input
                except Exception as e:
                    st.warning("Error processing input. Using raw input.")
                    corrected_input = user_input

                # Use the logged-in user's email and current chat title as session_id
                email = st.session_state.username  # Email from login
                session_id = st.session_state.selected_chat_title

                # Call chatbot_reply with email and session_id
                current_chat["messages"].append({"role": "user", "text": user_input})
                bot_reply = chatbot_reply(user_input, email=email, session_id=session_id)
                current_chat["messages"].append({"role": "bot", "text": bot_reply})
                save_user_chats(username, user_chats)
                st.rerun()