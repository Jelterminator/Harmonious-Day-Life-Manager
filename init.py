# File: init.py
#
# Run this file ONCE to authenticate with Google.

from main import Orchestrator
import time
import sys

if __name__ == "__main__":
    try:
        Orchestrator.create_initial_token()
    except Exception as e:
        print(f"\n--- An Error Occurred ---")
        print(f"Could not create token: {e}")
        print("Please ensure 'credentials.json' is in this folder.")
    
    print("\nThis window will close in 10 seconds...")
    time.sleep(10)
    sys.exit()