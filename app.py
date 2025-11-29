<<<<<<< HEAD
git add app.py
git commit -m "FINAL FIX: Force Streamlit to use new dependencies"
git push origin main

این Commit جدید باید Streamlit را مجبور کند که یک Build کامل انجام دهد و مشکل `tools` را که به خاطر Cache قدیمی بود، برطرف کند. **موفق باشید!**



=======
# FINAL FIX: Force Streamlit to rebuild cache (2025-11-28)
# import required libraries
>>>>>>> 0b7a4b8a6bcc02b576d760205264df7118a48bc0
import streamlit as st
import os
from google import genai
from google.genai import types

# --- Configuration ---
# Set page title and favicon
st.set_page_config(page_title="Rayan: AI Immigration Assistant", page_icon="🌐")

# Set the system instruction for the Gemini model
SYSTEM_INSTRUCTION = (
    "You are Rayan, an experienced and empathetic AI immigration assistant. "
    "Your core function is to provide helpful, general information, and analysis "
    "on immigration topics for Canada. When responding, you must adhere strictly to the following rules:\n"
    "1. You must only answer questions related to Canadian immigration, visas, and citizenship. "
    "2. If a user asks a question outside of Canadian immigration (e.g., travel, investment, other countries' laws), "
    "politely state that you are specialized in Canadian immigration and cannot assist with that specific query. "
    "3. Be friendly, encouraging, and clear in your explanations. "
    "4. Always mention that you are an AI and your information should not be considered official legal advice. "
    "5. Use the provided tools (if available) to analyze documents or perform complex calculations when relevant."
)

# --- Tool Functions ---
def analyze_document(document_summary: str) -> str:
    """
    Analyzes a document summary provided by the user (e.g., a visa requirement list,
    a specific policy text, or a letter from IRCC) and extracts key requirements,
    deadlines, and next steps.

    Args:
        document_summary: A summarized text provided by the user detailing the
                          content of their immigration document.

    Returns:
        A concise analysis highlighting critical information and actions needed.
    """
    # The model will use this function signature to generate a call with the user's summary.
    return f"Analysis complete for document summary: '{document_summary}'. The model will now interpret this summary based on its knowledge base."

def calculate_crs_score(age: int, education_level: str, work_experience_years: int, language_test_score: float) -> str:
    """
    Calculates an estimated Comprehensive Ranking System (CRS) score for Express Entry
    based on the key factors provided by the user.

    Args:
        age: The applicant's age.
        education_level: The highest level of education (e.g., 'Master's', 'Bachelor's').
        work_experience_years: Years of skilled work experience outside Canada.
        language_test_score: The CLB equivalent or IELTS overall score.

    Returns:
        A disclaimer stating that this is an estimate and a breakdown of the score based on the factors.
    """
    # This is a mock function; the actual score calculation logic is complex and changes often.
    # The model will use its training data to provide a detailed, but estimated, analysis based on the inputs.
    return (
        f"Based on the provided factors (Age: {age}, Education: {education_level}, "
        f"Work Exp: {work_experience_years} years, Language Score: {language_test_score}), "
        "the CRS score is complex to calculate accurately here. Rayan will provide an "
        "estimated score range and a detailed breakdown based on the latest available policy data."
    )


# --- Initialize Gemini Client and Chat ---
# Use the Streamlit secrets for the API key
try:
    if "GEMINI_API_KEY" not in os.environ:
        # Check Streamlit secrets first
        api_key = st.secrets["GEMINI_API_KEY"]
    else:
        api_key = os.environ["GEMINI_API_KEY"]
except KeyError:
    st.error("API key not found. Please set the 'GEMINI_API_KEY' in your Streamlit Secrets.")
    st.stop()
except Exception as e:
    st.error(f"An unexpected error occurred during API key retrieval: {e}")
    st.stop()


# Initialize the client and tools
@st.cache_resource
def get_gemini_client():
    """Initializes and returns the Gemini client."""
    return genai.Client(api_key=api_key)

client = get_gemini_client()

# Define available tools
available_tools = [analyze_document, calculate_crs_score]


# Initialize the chat session
@st.cache_resource(show_spinner="Initializing AI Assistant...")
def create_chat_session():
    """Creates a new chat session with the specified model, instructions, and tools."""
    try:
        # IMPORTANT: Using types.Tool as suggested by google-genai documentation for tool calling
        # The 'tools' argument is available from google-genai==1.52.0 onwards
        chat = client.chats.create(
            model="gemini-2.5-flash",
            system_instruction=SYSTEM_INSTRUCTION,
            tools=available_tools # Pass the function objects here
        )
        return chat
    except Exception as e:
        # Display the specific error that has been haunting us
        st.error(f"An error occurred while creating the chat session: {e}")
        st.stop()

chat = create_chat_session()


# --- Main Streamlit App Logic ---
st.title("🌐 Rayan: AI Immigration Assistant")
st.caption("Specialized in Canadian Immigration, powered by Gemini.")

# Initialize chat history in session state
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "assistant", "content": "سلام! من رایان هستم، مشاور هوش مصنوعی مهاجرت کانادا. چطور می‌توانم امروز به شما کمک کنم؟"}
    ]

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Function to handle tool responses
def handle_tool_call(tool_call):
    """Executes the function called by the model and sends the result back."""
    tool_name = tool_call.function.name
    tool_args = dict(tool_call.function.args)

    # 1. Look up the Python function by name
    if tool_name == "analyze_document":
        function_to_call = analyze_document
    elif tool_name == "calculate_crs_score":
        function_to_call = calculate_crs_score
    else:
        return f"Error: Unknown tool '{tool_name}' called."

    # 2. Execute the function with the arguments
    tool_output = function_to_call(**tool_args)

    # 3. Send the tool's output back to the model
    response = chat.send_message(
        "",  # Empty user input for tool response
        tool_outputs=[
            types.ToolOutput(
                name=tool_name,
                content=tool_output,
            )
        ],
    )
    return response.text # Return the final text response from the model

# Process user input
if prompt := st.chat_input("سؤال خود را در مورد مهاجرت کانادا بپرسید..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("در حال تحلیل..."):
            # Send message to the Gemini API
            try:
                response = chat.send_message(prompt)
                
                # Check for tool calls
                if response.function_calls:
                    full_response_text = ""
                    for tool_call in response.function_calls:
                        # Display the tool call to the user
                        st.info(f"Rayan is using the tool: **{tool_call.function.name}** with arguments: {dict(tool_call.function.args)}")
                        
                        # Handle the tool call and get the final response text
                        final_response = handle_tool_call(tool_call)
                        full_response_text += final_response
                        
                    st.session_state.messages.append({"role": "assistant", "content": full_response_text})
                    st.markdown(full_response_text)

                else:
                    # Normal text response
                    st.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})

            except Exception as e:
                error_message = f"An error occurred: {e}. Please check your API key and connection."
                st.error(error_message)
                st.session_state.messages.append({"role": "assistant", "content": error_message})        
