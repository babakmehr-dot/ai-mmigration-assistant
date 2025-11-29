import streamlit as st
import os
import json
from google import genai
from google.genai import types

# --- 1. Tool Definition (CRS Score Calculation) ---

def calculate_crs_score(age: int, education_level: str, language_score: int, work_experience_years: int) -> str:
    """
    Calculates an estimated Comprehensive Ranking System (CRS) score for Express Entry to Canada.
    CRS is based on factors like age, education, language proficiency (e.g., IELTS/CLB), and work experience.
    
    The function provides a simplified, illustrative score for demonstration.
    
    Args:
        age: The applicant's age in years (e.g., 30).
        education_level: The highest level of education (e.g., "Master's Degree", "Bachelor's Degree").
        language_score: The combined language proficiency score (e.g., CLB equivalent, simplified for demonstration, e.g., 100).
        work_experience_years: Years of skilled work experience (e.g., 3).
        
    Returns:
        A JSON string containing the estimated CRS score and a brief assessment.
    """
    
    # --- Simplified Scoring Logic (for demonstration only) ---
    score = 0
    
    # Age (Max 110 points)
    if 20 <= age <= 29:
        score += 110
    elif 30 <= age <= 35:
        score += 90
    else:
        score += 50
        
    # Education (Max 150 points)
    if "Master" in education_level or "PHD" in education_level:
        score += 135
    elif "Bachelor" in education_level:
        score += 120
    else:
        score += 80
        
    # Language (Max 160 points)
    if language_score >= 100:
        score += 130
    elif language_score >= 80:
        score += 100
    else:
        score += 60
        
    # Work Experience (Max 80 points)
    score += min(work_experience_years * 20, 80)
    
    # --- Final Output ---
    
    assessment = ""
    if score >= 480:
        assessment = "Your score is highly competitive based on recent Express Entry draws."
    elif score >= 450:
        assessment = "Your score is strong and competitive."
    else:
        assessment = "Your score is moderate and may require improvements in language or education."

    result = {
        "crs_score": score,
        "assessment": assessment,
        "note": "This is a simplified estimate for demonstration. The actual CRS calculation is more complex."
    }
    
    return json.dumps(result)


# --- 2. Streamlit Application Setup ---

st.set_page_config(page_title="Rayan: AI Immigration Assistant", page_icon="🇨🇦")
st.title("🇨🇦 Rayan: AI Immigration Assistant")

# Use st.secrets to securely load the API key
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except KeyError:
    st.error(
        "API key not found. Please set the 'GEMINI_API_KEY' environment variable in your Streamlit Secrets."
    )
    st.stop()

# Initialize the Gemini Client
try:
    client = genai.Client(api_key=api_key)
except Exception as e:
    st.error(f"Error initializing Gemini Client: {e}")
    st.stop()


# --- 3. Chat Session Management ---

if "chat" not in st.session_state:
    try:
        # Pass the function directly in the tools list
        st.session_state.chat = client.chats.create(
            model="gemini-2.5-flash",
            tools=[calculate_crs_score], # Pass the function object here
            system_instruction="You are Rayan, an expert AI Immigration Consultant specializing in Canadian Express Entry. "
                               "Your goal is to provide accurate and encouraging advice. "
                               "Only use the 'calculate_crs_score' tool when the user explicitly asks for a CRS score calculation or assessment and provides all necessary numerical data (age, education, language score, work experience)."
        )
    except Exception as e:
        st.error(f"An error occurred while creating the chat session: {e}")
        st.stop()
        

# --- 4. Display Chat History ---

# Custom function to handle tool calling and display the result
def handle_response(response):
    if response.function_calls:
        # The model wants to call a function (CRS Score)
        st.info("Rayan is performing the CRS calculation...")
        
        for func_call in response.function_calls:
            # 1. Get the arguments for the tool call
            func_name = func_call.name
            args = dict(func_call.args)

            # 2. Call the Python function
            if func_name == "calculate_crs_score":
                result = calculate_crs_score(**args)
                
                # 3. Send the result back to the model
                response = st.session_state.chat.send_message(
                    contents=result,
                    # Provide the function response in the correct format
                    tool_responses=[types.ToolResponse(
                        name=func_name, 
                        response={"result": result}
                    )]
                )
                
                # The model's final response will be the last item in the response list
                final_text = response.text
                st.markdown(final_text)
                return

    # If no function call, display the text response directly
    st.markdown(response.text)
    return


# Display history
for message in st.session_state.chat.get_history():
    role = "assistant" if message.role == "model" else "user"
    if message.role == "model":
        # Only show content parts that are text (ignore tool calls in history display)
        text_parts = [part.text for part in message.parts if hasattr(part, 'text')]
        if text_parts:
            with st.chat_message(role):
                st.markdown(text_parts[0])
    elif message.role == "user" and message.parts[0].text:
        with st.chat_message(role):
            st.markdown(message.parts[0].text)


# --- 5. User Input and Response Generation ---

if prompt := st.chat_input("Ask Rayan about Express Entry or CRS scores..."):
    # Display user prompt
    with st.chat_message("user"):
        st.markdown(prompt)

    # Send message to chat and handle potential tool calls
    try:
        response = st.session_state.chat.send_message(prompt)
        
        with st.chat_message("assistant"):
            handle_response(response)

    except Exception as e:
        st.error(f"An error occurred during response generation: {e}")
