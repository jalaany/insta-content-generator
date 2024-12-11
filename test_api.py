import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

# Configure API key
api_key = ""
genai.configure(api_key=api_key)

try:
    # Initialize the model
    model = genai.GenerativeModel('gemini-pro')
    
    # Simple test prompt
    response = model.generate_content("Say 'Hello World!'")
    
    print("API Key Test Results:")
    print("API Key:", api_key)
    print("Response:", response.text)
    
except Exception as e:
    print("Error testing API key:")
    print(str(e))
