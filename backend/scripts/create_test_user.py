import os
import sys
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("Error: SUPABASE_URL or SUPABASE_KEY not found in .env")
    sys.exit(1)

supabase: Client = create_client(url, key)

EMAIL = "physician@medico.ai"
PASSWORD = "MedicoTest2026!"

def create_user():
    try:
        print(f"Attempting to register user: {EMAIL}...")
        res = supabase.auth.sign_up({
            "email": EMAIL,
            "password": PASSWORD,
        })
        if res.user:
            print(f"Successfully created user: {res.user.email}")
        else:
            print("Registration attempt completed. If user exists, check login.")
    except Exception as e:
        if "User already registered" in str(e):
            print(f"User {EMAIL} already exists.")
        else:
            print(f"Error creating user: {e}")

if __name__ == "__main__":
    create_user()
