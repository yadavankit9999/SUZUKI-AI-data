def main():
    import streamlit as st
    import google.generativeai as genai
    import os
    from dotenv import load_dotenv
    import re
    import pandas as pd
    import io

    load_dotenv()
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-2.5-flash')

    # Function to get response from Gemini
    def get_gemini_response(prompt):
        response = model.generate_content(prompt)
        return response.text

    def extract_questions(survey_text):
        # Only extract lines that look like actual questions (numbered, bulleted, or ending with a question mark)
        lines = survey_text.split('\n')
        questions = []
        in_code_block = False
        for line in lines:
            line = line.strip()
            if line.startswith('```'):
                in_code_block = not in_code_block
                continue
            if in_code_block or not line:
                continue
            if re.match(r"^\d+\.\s*.+", line):
                questions.append(re.sub(r"^\d+\.\s*", "", line))
            elif re.match(r"^[-*]\s*.+", line):
                questions.append(re.sub(r"^[-*]\s*", "", line))
            elif line.endswith('?') and len(line) > 8:
                questions.append(line)
        return questions

    # Streamlit App
    st.set_page_config(page_title="Suzuki Survey Questionnaire Builder", page_icon="Suzuki logo.jpg")



    st.title("Suzuki Survey Questionnaire Builder")

    # Initialize chat history and state in session state
    if 'chat_history' not in st.session_state:
        st.session_state['chat_history'] = []
        st.session_state['app_state'] = 'GREETING'
        st.session_state['requirements'] = {}
        st.session_state['ai_summary'] = ""

    # Display chat history
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Initial greeting from the chatbot
    if st.session_state.app_state == 'GREETING':
        initial_prompt = "Hello Suzuki team! I am your dedicated survey preparation assistant, designed specifically for Suzuki's needs. I can help you create a questionnaire for your projects, product planning, or customer feedback. Please be as specific as possible. To start, could you please provide the main topic, agenda, and objectives for your survey? (You can write them in a single message, separated by commas or new lines.)"
        st.session_state.chat_history.append({"role": "assistant", "content": initial_prompt})
        st.session_state.app_state = 'GATHERING_TOPIC_AGENDA_OBJECTIVES'
        st.rerun()

    # Handle user input
    if user_input := st.chat_input("Your response..."):
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # State machine for conversation flow
        current_state = st.session_state.app_state

        if current_state == 'GATHERING_TOPIC_AGENDA_OBJECTIVES':
            # Try to split input into topic, agenda, objectives
            parts = [p.strip() for p in user_input.split('\n') if p.strip()]
            if len(parts) < 3:
                parts = [p.strip() for p in user_input.split(',') if p.strip()]
            st.session_state.requirements['topic'] = parts[0] if len(parts) > 0 else user_input
            st.session_state.requirements['agenda'] = parts[1] if len(parts) > 1 else ""
            st.session_state.requirements['objectives'] = parts[2] if len(parts) > 2 else ""
            response = "Great! Now, please provide the target audience, age groups, and any other demographics we should consider (e.g., location, profession). You can write them in a single message, separated by commas or new lines."
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            st.session_state.app_state = 'GATHERING_AUDIENCE_AGE_DEMO'
            st.rerun()

        elif current_state == 'GATHERING_AUDIENCE_AGE_DEMO':
            # Try to split input into audience, age_groups, demographics
            parts = [p.strip() for p in user_input.split('\n') if p.strip()]
            if len(parts) < 3:
                parts = [p.strip() for p in user_input.split(',') if p.strip()]
            st.session_state.requirements['audience'] = parts[0] if len(parts) > 0 else user_input
            st.session_state.requirements['age_groups'] = parts[1] if len(parts) > 1 else ""
            st.session_state.requirements['demographics'] = parts[2] if len(parts) > 2 else ""
            response = "What type of questions do you want to include? (e.g., multiple choice, open-ended, rating scale)"
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            st.session_state.app_state = 'GATHERING_Q_TYPE'
            st.rerun()

        elif current_state == 'GATHERING_Q_TYPE':
            st.session_state.requirements['question_types'] = user_input
            response = "Roughly how many questions should be in the survey?"
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            st.session_state.app_state = 'GATHERING_NUM_QUESTIONS'
            st.rerun()

        elif current_state == 'GATHERING_NUM_QUESTIONS':
            st.session_state.requirements['num_questions'] = user_input
            response = "Any other info you want to provide? (e.g. existing feedback, outcomes from old surveys, industry reports, or raw survey responses)"
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            st.session_state.app_state = 'GATHERING_EXISTING_CONTEXT'
            st.rerun()

        elif current_state == 'GATHERING_EXISTING_CONTEXT':
            st.session_state.requirements['existing_context'] = user_input
            with st.spinner("Summarizing your requirements..."):
                summarization_prompt = f"""
                This survey is for Indian users. Use Indian context for all questions, including currency (INR), locations, and demographics.
                Please provide a concise summary of the following survey requirements. Do not use code formatting or markdown. Output plain text only.\n- **Topic:** {st.session_state.requirements.get('topic')}\n- **Agenda:** {st.session_state.requirements.get('agenda')}\n- **Objectives:** {st.session_state.requirements.get('objectives')}\n- **Target Audience:** {st.session_state.requirements.get('audience')}\n- **Target Age Groups:** {st.session_state.requirements.get('age_groups')}\n- **Demographics:** {st.session_state.requirements.get('demographics')}\n- **Question Types:** {st.session_state.requirements.get('question_types')}\n- **Number of Questions:** {st.session_state.requirements.get('num_questions')}\n- **Other Info:** {st.session_state.requirements.get('existing_context')}\n"""
                ai_summary = get_gemini_response(summarization_prompt)
                st.session_state['ai_summary'] = ai_summary

            confirmation_message = f"""
            Here is a summary of your requirements:

            {st.session_state['ai_summary']}

            Does this look correct, or would you like to add or change anything?
            """
            st.session_state.chat_history.append({"role": "assistant", "content": confirmation_message})
            st.session_state.app_state = 'SUMMARIZING'
            st.rerun()

        elif current_state == 'SUMMARIZING':
            if "yes" in user_input.lower() or "correct" in user_input.lower():
                generation_prompt = f"""
                This survey is for Indian users. Use Indian context for all questions, including currency (INR), locations, and demographics.
                Based on the following raw user responses and AI-generated summary, please generate a comprehensive survey questionnaire. Do not use code formatting or markdown. Output plain text only.

                **Raw User Responses:**
                - Topic: {st.session_state.requirements.get('topic')}
                - Agenda: {st.session_state.requirements.get('agenda')}
                - Objectives: {st.session_state.requirements.get('objectives')}
                - Target Audience: {st.session_state.requirements.get('audience')}
                - Target Age Groups: {st.session_state.requirements.get('age_groups')}
                - Demographics: {st.session_state.requirements.get('demographics')}
                - Question Types: {st.session_state.requirements.get('question_types')}
                - Number of Questions: {st.session_state.requirements.get('num_questions')}
                - Other Info: {st.session_state.requirements.get('existing_context')}

                **AI-Generated Summary:**
                {st.session_state.get('ai_summary')}

                Please create a detailed survey questionnaire that incorporates all the specific details from the raw responses while following the structure and insights from the AI summary.
                """
                with st.spinner("Generating your survey questions..."):
                    survey_questions = get_gemini_response(generation_prompt)
                    st.session_state.chat_history.append({"role": "assistant", "content": survey_questions})
                    st.session_state.chat_history.append({"role": "assistant", "content": "Would you like to start over?"})
                    st.session_state.app_state = 'DONE'
                    st.rerun()
            else:
                response = "Please tell me what you would like to change or add."
                st.session_state.chat_history.append({"role": "assistant", "content": response})
                st.session_state.app_state = 'UPDATING_REQUIREMENTS'
                st.rerun()

        elif current_state == 'UPDATING_REQUIREMENTS':
            with st.spinner("Updating requirements..."):
                update_prompt = f"""
                This survey is for Indian users. Use Indian context for all questions, including currency (INR), locations, and demographics.
                The user wants to update their survey requirements. The previously gathered details are listed below, followed by the user's requested changes. Generate a new, concise summary that incorporates these changes. Do not use code formatting or markdown. Output plain text only.

                **Previously Gathered Details:**
                - Topic: {st.session_state.requirements.get('topic')}
                - Agenda: {st.session_state.requirements.get('agenda')}
                - Objectives: {st.session_state.requirements.get('objectives')}
                - Target Audience: {st.session_state.requirements.get('audience')}
                - Target Age Groups: {st.session_state.requirements.get('age_groups')}
                - Demographics: {st.session_state.requirements.get('demographics')}
                - Question Types: {st.session_state.requirements.get('question_types')}
                - Number of Questions: {st.session_state.requirements.get('num_questions')}
                - Other Info: {st.session_state.requirements.get('existing_context')}

                **User's Requested Changes:**
                "{user_input}"

                Please generate an updated summary based on these changes.
                """
                updated_summary = get_gemini_response(update_prompt)
                st.session_state['ai_summary'] = updated_summary

            confirmation_message = f"""
            Here is the updated summary of your requirements:

            {st.session_state['ai_summary']}

            Does this look correct now? Or are there more changes?
            """
            st.session_state.chat_history.append({"role": "assistant", "content": confirmation_message})
            st.session_state.app_state = 'SUMMARIZING'
            st.rerun()
        
        elif current_state == 'DONE':
            if "yes" in user_input.lower():
                st.session_state.app_state = 'GREETING'
                st.session_state.chat_history = []
                st.session_state.requirements = {}
                st.session_state['ai_summary'] = ""
                st.rerun()
            else:
                response = "Thank you for using the survey bot! Goodbye."
                st.session_state.chat_history.append({"role": "assistant", "content": response})
                st.rerun()

    # After survey generation, allow review/edit/freeze
    if st.session_state.get('app_state') == 'DONE' and st.session_state.chat_history:
        # Find the last AI survey questions
        survey_text = None
        for msg in reversed(st.session_state.chat_history):
            if msg['role'] == 'assistant' and 'Would you like to start over?' not in msg['content']:
                survey_text = msg['content']
                break
        if survey_text:
            if 'survey_questions' not in st.session_state:
                st.session_state['survey_questions'] = extract_questions(survey_text)
            
            if not st.session_state.get('edit_mode'):
                if st.button("Edit / Ask AI to modify questions", key="edit_ai_btn"):
                    st.session_state['edit_mode'] = True
                    st.session_state['edit_prompt'] = ""
                    st.rerun()
            else:
                st.info("Enter your instructions below (e.g., 'Rephrase question 3', 'Add a question about job', 'Add an income range for less than 25k', etc.) and press Enter.")
                edit_input = st.text_input("Your edit instructions:", key="edit_input")
                if edit_input:
                    # Send current questions and user instructions to Gemini
                    edit_prompt = (
                        "Here is the current list of survey questions as a Python list (do not use code formatting or markdown, output plain text only):\n" +
                        str(st.session_state['survey_questions']) +
                        "\n\nThe user wants to make the following changes: " + edit_input +
                        "\nReturn the updated list of questions as a Python list of strings, plain text only, no code formatting or markdown."
                    )
                    ai_edit_response = get_gemini_response(edit_prompt)
                    import ast
                    try:
                        updated_questions = ast.literal_eval(ai_edit_response)
                        st.session_state['survey_questions'] = updated_questions
                        # Reset edit mode
                        st.session_state['edit_mode'] = False
                        st.rerun()
                    except Exception:
                        st.error("AI could not parse the updated questions. Please try again or rephrase your instructions.")
            if st.button("Freeze & Download Excel", key="freeze_btn"):
                # Use AI to generate column names
                with st.spinner("Generating Excel template..."):
                    col_prompt = (
                        "For each of these survey questions, suggest a short, clear column name (max 25 chars, all caps, no spaces, underscores allowed). "
                        "Return as a Python list of dicts: [{\"question\": ..., \"column\": ...}] Plain text only, no code formatting or markdown.\n\nQuestions:\n" +
                        '\n'.join(st.session_state['survey_questions'])
                    )
                    ai_col_response = get_gemini_response(col_prompt)
                    # Try to safely eval the AI's output
                    import ast
                    try:
                        col_map = ast.literal_eval(ai_col_response)
                        columns = [item['column'] for item in col_map]
                    except Exception:
                        # fallback: use questions as columns
                        columns = [f"Q{i+1}" for i in range(len(st.session_state['survey_questions']))]
                    df = pd.DataFrame(columns=columns)
                    output = io.BytesIO()
                    df.to_excel(output, index=False)
                    st.session_state['excel_data'] = output.getvalue()
                st.session_state['survey_frozen'] = True
                st.rerun()

            if st.session_state.get('survey_frozen'):
                st.success("Survey frozen. You can now download the file or start a new survey.")
                if st.session_state.get('excel_data'):
                    st.download_button(
                        label="Download Survey Excel Template",
                        data=st.session_state['excel_data'],
                        file_name="suzuki_survey_template.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                if st.button("Start New Survey", key="restart_btn"):
                    for k in ['chat_history','app_state','requirements','ai_summary','survey_questions','survey_frozen','edit_mode','edit_prompt', 'excel_data']:
                        if k in st.session_state:
                            del st.session_state[k]
                    st.rerun()

if __name__ == "__main__":
    main() 