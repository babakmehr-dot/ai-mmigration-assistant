import streamlit as st
import os
import json # Essential for parsing the structured JSON output
from google import genai
from pydantic import BaseModel, Field
from typing import Optional

# ----------------------------------------------------
# 1. CLIENT INITIALIZATION (Secure Key Handling)
# ----------------------------------------------------
def initialize_client():
    """Initializes the Gemini Client using the securely stored API Key."""
    # The API Key is loaded from the environment variable GEMINI_API_KEY
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            st.error(
                "API Key not found. Please set the 'GEMINI_API_KEY' environment variable "
                "in your Streamlit, Kaggle, or Replit Secrets."
            )
            return None
            
        client = genai.Client(api_key=api_key)
        st.sidebar.success("Gemini Client initialized.")
        return client
        
    except Exception as e:
        st.error(f"Error initializing Gemini Client: {e}")
        return None

# ----------------------------------------------------
# 2. STRUCTURED OUTPUT SCHEMA (Mandatory Requirement)
# ----------------------------------------------------
class ImmigrationData(BaseModel):
    """Schema for extracting structured data from documents for immigration forms."""
    full_name: str = Field(description="The full name of the applicant as found on the document.")
    date_of_birth: str = Field(description="Date of birth in YYYY-MM-DD format (or similar format).")
    job_title: str = Field(description="Primary job title from the employment letter.")
    noc_code: str = Field(description="National Occupation Classification (NOC) code determined by matching the job title to Canadian standards.")
    wes_equivalency: str = Field(description="Canadian educational equivalency from the WES or educational assessment report (e.g., 'Master's degree', 'Bachelor's degree').")

# ----------------------------------------------------
# 3. TOOL DEFINITION (Mandatory Requirement)
# ----------------------------------------------------
def calculate_crs_score(education: str, experience_years: int, language_score_clb: int) -> dict:
    """
    Calculates an ESTIMATED Comprehensive Ranking System (CRS) score for Express Entry.
    The score is based on key factors: Education, Experience, and Language (CLB).
    
    Args:
        education (str): The highest level of education (e.g., 'Master's degree').
        experience_years (int): Number of years of skilled work experience.
        language_score_clb (int): The Comprehensive Language Benchmark (CLB) score.
    """
    # NOTE: This is a highly simplified, non-official placeholder calculation for demonstration.
    score = 0
    
    # 1. Education Points (Simplified)
    if "Master" in education or "PhD" in education:
        score += 135
    elif "Bachelor" in education:
        score += 120
    else:
        score += 30

    # 2. Experience Points (Simplified)
    # Max points for 5+ years
    score += min(experience_years, 5) * 15 

    # 3. Language Points (Simplified)
    # Give a bonus for high language scores
    if language_score_clb >= 9:
        score += language_score_clb * 10
    else:
        score += language_score_clb * 5
        
    return {"calculated_score": score, "note": "CRS score is a simplified estimate for project demonstration only."}


# ----------------------------------------------------
# 4. MAIN APPLICATION FUNCTION (PDF, Chat, and Tool Logic)
# ----------------------------------------------------
def main():
    st.set_page_config(page_title="Rayan: AI Immigration Assistant", layout="wide")
    st.title("🇨🇦 Rayan: AI Immigration Assistant")
    
    # Initialize the client
    client = initialize_client()
    if not client:
        return # Stop if client failed to initialize

    # Session State Initialization for Chat History
    if 'chat' not in st.session_state:
        # Initialize the chat session, making the Tool available
        st.session_state.chat = client.chats.create(
            model="gemini-2.5-flash", 
            tools=[calculate_crs_score] # Register the tool
        )
        st.session_state.extraction_done = False # Flag to track if the main extraction is complete
        st.session_state.uploaded_file_bytes = None # To hold the file data

    # Sidebar for File Upload and Instructions
    with st.sidebar:
        st.header("Upload Document")
        uploaded_file = st.file_uploader(
            "Upload your document (PDF, DOCX, TXT accepted)", 
            type=["pdf", "docx", "txt"]
        )
        
        st.markdown("---")
        st.markdown("### How to Use")
        st.info(
            "1. **Upload your PDF** document on the left.\n"
            "2. Click the **'Analyze Document'** button to extract structured data.\n"
            "3. Use the chat box for follow-up questions or **request a calculation** (e.g., 'What is my estimated CRS score?').",
            icon="ℹ️"
        )
        
        # Logic to handle the file upload and analysis trigger
        if uploaded_file and st.button("Analyze Document for Extraction"):
            st.session_state.uploaded_file_bytes = uploaded_file.getvalue()
            st.session_state.extraction_done = False
            # Store mime type for API
            st.session_state.uploaded_mime_type = f"application/{uploaded_file.name.split('.')[-1]}"
            st.session_state.uploaded_file_name = uploaded_file.name
            st.rerun() # Rerun to start the extraction process

    # Document Analysis and Initial Extraction Logic
    if st.session_state.uploaded_file_bytes and not st.session_state.extraction_done:
        
        # Convert file bytes to a Part object for Gemini
        file_part = genai.types.Part.from_bytes(
            data=st.session_state.uploaded_file_bytes,
            mime_type=st.session_state.uploaded_mime_type
        )
        
        # Prompt for Structured Data Extraction
        prompt = (
            f"Analyze the attached document named '{st.session_state.uploaded_file_name}'. "
            "Extract all necessary structured data points needed for an Express Entry profile. "
            "Crucially, determine the approximate NOC code and the educational equivalency. "
            "Return the entire response exclusively as a JSON object matching the requested schema."
        )

        with st.spinner("Analyzing document and extracting structured data..."):
            try:
                # Send the file (Part) and the prompt to the chat
                response = st.session_state.chat.send_message(
                    contents=[prompt, file_part],
                    config=genai.types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=ImmigrationData, # Enforce Pydantic schema here
                    )
                )
                
                # Update chat history with the response content (The response is the JSON text)
                st.session_state.chat.get_history() 
                
                # Display the extracted JSON data
                st.success("✅ Structured Data Extracted Successfully!")
                extracted_data = json.loads(response.text)
                
                st.markdown("### 📊 Extracted Immigration Metadata (JSON)")
                st.json(extracted_data)
                
                st.session_state.extraction_done = True
                
            except Exception as e:
                st.error(f"Error during document analysis: {e}")
                st.warning("Please try uploading a different document or check the document format.")
                st.session_state.uploaded_file_bytes = None
                
    # Main Chat Interface and History Display
    st.markdown("---")
    
    # Display historical messages
    for message in st.session_state.chat.get_history():
        # Skip the system instruction messages, focusing on User/Agent interaction
        if message.role in ["user", "model"]:
            role = "user" if message.role == "user" else "assistant"
            with st.chat_message(role):
                # If the message contains a tool call, display the call parameters
                if message.parts and message.parts[0].function_call:
                    st.caption("🤖 Agent called Tool:")
                    st.json(message.parts[0].function_call.to_dict())
                # If the message contains tool output, display that
                elif message.parts and message.parts[0].function_response:
                    st.caption("🛠️ Tool Response:")
                    st.json(message.parts[0].function_response.to_dict())
                # Otherwise, display the text content
                elif message.parts and message.parts[0].text:
                    st.markdown(message.parts[0].text)
        
    # User input
    if prompt := st.chat_input("Ask your immigration question (e.g., 'What is my estimated CRS score?')..."):
        
        # Add user prompt to history and display
        with st.chat_message("user"):
            st.markdown(prompt)
            
        # Send prompt to the agent
        with st.spinner("Thinking..."):
            response = st.session_state.chat.send_message(prompt)
            
        # Check if the agent wants to call a tool (CRS calculation)
        if response.function_calls:
            # Handle tool calling
            for func_call in response.function_calls:
                
                if func_call.name == "calculate_crs_score":
                    args = dict(func_call.args)
                    st.info(f"The assistant is calculating the CRS score with arguments: {args}")
                    
                    # Execute the actual Python tool function
                    # Ensure all arguments are passed as required by the function signature
                    tool_output = calculate_crs_score(**args)
                    
                    # Send tool output back to the model for a natural language summary
                    tool_response = st.session_state.chat.send_message(
                        contents=genai.types.Part.from_function_response(
                            name=func_call.name,
                            response=tool_output
                        )
                    )
                    # Display the final text response from the agent after tool execution
                    with st.chat_message("assistant"):
                        st.markdown(tool_response.text)
                        
        else:
            # Regular text response
            with st.chat_message("assistant"):
                st.markdown(response.text)

if __name__ == "__main__":
    main()
