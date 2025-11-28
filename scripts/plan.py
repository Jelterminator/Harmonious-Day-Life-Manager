"""
Daily schedule planner entry point.
Run this file every day to generate your schedule.
Make sure you have run 'python scripts/setup.py' at least once.
"""

import sys
import time
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Imports
from src.core.orchestrator import OrchestratorFactory
from src.core.config_manager import Config
from src.core.anchor_manager import AnchorManager  # <--- New Import
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

def main() -> int:
    """
    Main execution function.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    start_time = time.time()
    
    logger.info("="*60)
    logger.info("Starting Harmonious Day Planner")
    logger.info("="*60)
    
    try:
        # ---------------------------------------------------------
        # STEP 1: Generate Today's Anchor Configuration
        # ---------------------------------------------------------
        logger.info("Calculating Solar Phases & Fixed Anchors...")
        anchor_manager = AnchorManager(PROJECT_ROOT)
        
        if not anchor_manager.generate_daily_config():
            logger.error("Failed to generate anchor configuration.")
            logger.error("Please ensure database is set up correctly via scripts/setup.py")
            return 1
            
        logger.info("Daily configuration updated.")

        # ---------------------------------------------------------
        # STEP 2: Validate Full Configuration
        # ---------------------------------------------------------
        if not Config.validate():
            logger.error("Configuration validation failed")
            logger.error("Please run 'python scripts/setup.py' to configure the application")
            return 1
        
        logger.info("Configuration validated successfully")
        
        # ---------------------------------------------------------
        # STEP 3: Run Orchestrator
        # ---------------------------------------------------------
        logger.info("Initializing Orchestrator...")
        orchestrator = OrchestratorFactory.create()
        
        # Run the daily plan
        logger.info("Running daily plan generation...")
        success = orchestrator.run_daily_plan()
        
        elapsed = time.time() - start_time
        
        if success:
            logger.info("="*60)
            logger.info(f"Plan generation completed successfully in {elapsed:.2f} seconds")
            logger.info("="*60)
            return 0
        else:
            logger.error("="*60)
            logger.error(f"Plan generation failed after {elapsed:.2f} seconds")
            logger.error("="*60)
            return 1
            
    except FileNotFoundError as e:
        logger.error("Missing required file", exc_info=True)
        logger.error(f"Could not find: {e.filename}")
        return 1
        
    except ConnectionError as e:
        logger.error("Authentication failed", exc_info=True)
        logger.error(str(e))
        return 1
        
    except KeyboardInterrupt:
        logger.warning("Plan generation interrupted by user")
        return 1
        
    except Exception as e:
        logger.error("Unexpected fatal error", exc_info=True)
        logger.error(f"Error: {e}")
        return 1
    
    finally:
        elapsed = time.time() - start_time
        logger.info(f"Total execution time: {elapsed:.2f} seconds")


if __name__ == "__main__":
    exit_code = main()
    
    if exit_code != 0:
        print("\nPress Enter to exit...")
        input()
    
    sys.exit(exit_code)