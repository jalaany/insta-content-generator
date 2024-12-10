import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key
api_key = os.getenv('GOOGLE_API_KEY')
print(f"Using API key: {api_key[:10]}...")

try:
    # Configure Gemini
    genai.configure(api_key=api_key)
    
    # Initialize model
    model = genai.GenerativeModel('gemini-pro')
    
    # Simple test
    response = model.generate_content("Say hello!")
    print("\nTest Response:", response.text)
    
except Exception as e:
    print("\nError occurred:")
    print(str(e))
