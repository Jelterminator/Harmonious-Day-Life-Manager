# File: plan.py
#
# Run this file every day to generate your schedule.
# Make sure you have run 'init.py' at least once.

from main import Orchestrator
import sys
import time

if __name__ == "__main__":
    start_time = time.time()
    try:
        # 1. Create the Orchestrator
        # __init__ automatically loads configs and authenticates
        orchestrator = Orchestrator()
        
        # 2. Tell it to run the plan
        orchestrator.run_daily_plan()
        
    except FileNotFoundError as e:
        print("\n❌ ERROR: Missing File")
        print(f"Could not find: {e.filename}")
        print("Please make sure config.json and credentials.json exist.")
    except ConnectionError as e:
        print("\n❌ ERROR: Authentication Failed")
        print(f"{e}")
        print("Please try running 'init.py' again.")
    except Exception as e:
        print("\n❌ UNKNOWN FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        
    end_time = time.time()
    print(f"\n--- Total execution time: {end_time - start_time:.2f} seconds ---")
    
    print("\nThis window will close in 30 seconds...")
    time.sleep(30)
    sys.exit()