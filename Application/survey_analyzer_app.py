def main():
    import streamlit as st
    import pandas as pd
    import google.generativeai as genai
    import os
    from dotenv import load_dotenv
    import matplotlib.pyplot as plt
    import seaborn as sns
    import io

    load_dotenv()
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-2.5-flash')

    def get_gemini_response(prompt):
        response = model.generate_content(prompt)
        return response.text

    st.set_page_config(page_title="Suzuki Survey Analyzer", page_icon="Suzuki logo.jpg")
    st.title("Suzuki Survey Analyzer")
    st.markdown("Upload your completed survey data to generate insights, visualizations, and actionable recommendations.")

    if 'analyzer_chat_history' not in st.session_state:
        st.session_state['analyzer_chat_history'] = []
    if 'df' not in st.session_state:
        st.session_state['df'] = None
    if 'data_profile' not in st.session_state:
        st.session_state['data_profile'] = None

    uploaded_file = st.file_uploader("Choose a CSV or Excel file", type=["csv", "xlsx"])

    if uploaded_file is not None and st.session_state.df is None:
        with st.spinner('Analyzing your data...'):
            try:
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)
                st.session_state.df = df

                # Generate data profile for AI context
                profile_buffer = io.StringIO()
                st.session_state.df.info(buf=profile_buffer)
                profile_info = profile_buffer.getvalue()
                data_profile = f"""
                Data Summary:
                - Shape: {st.session_state.df.shape}
                - Columns and Data Types:
                {profile_info}
                - Descriptive Statistics:
                {st.session_state.df.describe().to_string()}
                - First 5 rows:
                {st.session_state.df.head().to_string()}
                """
                st.session_state.data_profile = data_profile
                st.session_state.analyzer_chat_history.append({"role": "assistant", "content": "Your data has been loaded and analyzed. What would you like to know?"})

            except Exception as e:
                st.error(f"Failed to load or process the file: {e}")

    if st.session_state.df is not None:
        st.subheader("Data Preview")
        st.dataframe(st.session_state.df.head())

        # Display chat history
        for message in st.session_state.analyzer_chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if "figure" in message:
                    st.pyplot(message["figure"])

        if user_input := st.chat_input("Ask about your data..."):
            st.session_state.analyzer_chat_history.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)

            with st.spinner("Thinking..."):
                # Get last 3 chat messages for context
                chat_context = "\n".join([
                    f"{m['role'].capitalize()}: {m['content']}" for m in st.session_state.analyzer_chat_history[-3:] if 'content' in m
                ])
                prompt = f"""
                You are an expert data analyst for Suzuki. Your task is to analyze the provided survey data based on user requests.

                You must only use the uploaded survey data and the provided data profile for your answers. Do not use any outside knowledge or make up information. If the answer cannot be found in the data, say so clearly.

                Here is a profile of the data:
                {st.session_state.data_profile}

                Recent conversation context:
                {chat_context}

                The user's current request is: "{user_input}"

                If the user refers to a previous plot, use the last plot's variables as context and update the axes or plot type accordingly.

                Based on the user's request, decide on ONE of the following actions:
                1.  **Answer Directly**: If the question can be answered from the data profile or is a general query.
                2.  **Generate Python Code**: If the user wants a visualization or a specific data manipulation. The code should use the pandas DataFrame `df` and generate a plot using Matplotlib or Seaborn. The plot must be assigned to a variable `fig`.
                3.  **Summarize Text**: If the user wants to understand qualitative feedback from a specific column. Identify the column name.

                Respond with a JSON object ONLY, in one of the following formats:
                - For a direct answer: {{"type": "answer", "content": "Your textual answer here."}}
                - For a plot: {{"type": "python", "code": "import matplotlib.pyplot as plt\nimport seaborn as sns\nfig, ax = plt.subplots()\n# Your code here, using 'df'\nsns.histplot(df['AGE'], ax=ax)\nax.set_title('Age Distribution')"}}
                - For a summary: {{"type": "summary", "column": "COLUMN_NAME"}}
                """
                ai_response_str = get_gemini_response(prompt).strip()

                try:
                    import json
                    # Clean the response to make it valid JSON
                    ai_response_str = ai_response_str.strip().replace('```json', '').replace('```', '').strip()
                    ai_response = json.loads(ai_response_str)

                    response_type = ai_response.get("type")
                    bot_message = {"role": "assistant"}

                    if response_type == "answer":
                        bot_message["content"] = ai_response.get("content", "I am not sure how to answer that.")
                    
                    elif response_type == "python":
                        code_to_execute = ai_response.get("code")
                        bot_message["content"] = f"Certainly! Here is the plot you requested.\n"
                        
                        # Execute the code
                        local_scope = {"df": st.session_state.df, "plt": plt, "sns": sns, "pd": pd}
                        exec(code_to_execute, local_scope)
                        bot_message["figure"] = local_scope.get('fig')

                    elif response_type == "summary":
                        column_to_summarize = ai_response.get("column")
                        if column_to_summarize in st.session_state.df.columns:
                            text_data = "\n".join(st.session_state.df[column_to_summarize].dropna().astype(str).tolist())
                            summary_prompt = f"Summarize the following user feedback from the Suzuki survey. Identify key themes, positive points, and areas for improvement.\n\nFeedback:\n{text_data}"
                            summary = get_gemini_response(summary_prompt)
                            bot_message["content"] = f"Here is a summary of the '{column_to_summarize}' column:\n\n{summary}"
                        else:
                            bot_message["content"] = f"I couldn't find the column '{column_to_summarize}' to summarize."

                    st.session_state.analyzer_chat_history.append(bot_message)
                    st.rerun()

                except (json.JSONDecodeError, Exception) as e:
                    st.error(f"Sorry, I had trouble processing that request. Please try again. Error: {e}")

if __name__ == "__main__":
    main() 