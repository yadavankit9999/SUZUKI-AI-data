import streamlit as st
import sys
from pathlib import Path

# Import the main functions from the other apps
sys.path.append(str(Path(__file__).parent))
from streamlit_app import main as survey_main
from survey_analyzer_app import main as analyzer_main
from file_translator_app import main as translator_main
from translator_google_app import main as google_translator_main

# Only import web_search here, do not change UI
import web_search

def web_search_main():
    st.title("🔎 Model Data Gathering")
    st.info("This feature will allow you to search the web and use AI to summarize or extract information. Stay tuned!")

# Sidebar navigation    # Sidebar with Suzuki branding
with st.sidebar:
    st.image("https://cdn.suzukimotorcycle.co.in/public-live/images/website/logo.jpg", width=300)
    st.sidebar.title("SUZUKI AI APPS")
    app_choice = st.sidebar.radio(
        "Choose an app:",
        [
            "Survey Questionnaire Builder",
            "Survey Analyzer",
            "File Translator (OCR, Hindi/Japanese)",
            "File Translator (Google API)",
            "Model Data Fetching (Web search)"
        ]
    )

# Main area: load the selected app
if app_choice == "Survey Questionnaire Builder":
    survey_main()
elif app_choice == "Survey Analyzer":
    analyzer_main()
elif app_choice == "File Translator (OCR, Hindi/Japanese)":
    translator_main()
elif app_choice == "File Translator (Google API)":
    google_translator_main()
elif app_choice == "Model Data Fetching (Web search)":
    web_search.main()
else:
    web_search_main() 