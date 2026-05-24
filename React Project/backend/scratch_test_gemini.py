import os
import sys
from dotenv import load_dotenv

# Load env variables from backend/.env
load_dotenv()

project_id = os.getenv("GCP_PROJECT_ID")
location = os.getenv("GCP_LOCATION")

print(f"Loaded GCP_PROJECT_ID: {project_id}")
print(f"Loaded GCP_LOCATION: {location}")

if not project_id:
    print("Error: GCP_PROJECT_ID is not set in the .env file!")
    sys.exit(1)

try:
    print("Importing google.genai...")
    from google import genai
    from google.genai import types
    
    print("Initializing genai.Client with Vertex AI...")
    client = genai.Client(vertexai=True, project=project_id, location=location)
    
    print("Sending test prompt to gemini-2.5-flash...")
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=["Verify if the Gemini API is working properly. Respond with a success message."]
    )
    
    print("\n--- RESPONSE FROM GEMINI ---")
    print(response.text)
    print("----------------------------\n")
    print("Gemini API is working successfully!")
except Exception as e:
    print(f"\n--- ERROR OCCURRED ---")
    import traceback
    traceback.print_exc()
    print("----------------------\n")
