import importlib
import pkgutil
import logging
from pathlib import Path

# Configure local logger
logger = logging.getLogger("BuddAI-Skills")

def load_registry():
    """
    Dynamically discovers and loads skill modules from the current directory.
    Returns a dictionary mapping skill IDs to their executable functions and metadata.
    """
    registry = {}
    package_dir = Path(__file__).parent
    
    # Iterate over all .py files in this directory
    for _, name, _ in pkgutil.iter_modules([str(package_dir)]):
        try:
            # Import the module relative to this package
            module = importlib.import_module(f".{name}", __package__)
            
            # Verify the Skill Interface (must have 'meta' and 'run')
            if hasattr(module, "meta") and hasattr(module, "run"):
                metadata = module.meta()
                skill_id = name
                
                registry[skill_id] = {
                    "name": metadata.get("name", skill_id),
                    "triggers": metadata.get("triggers", []),
                    "description": metadata.get("description", "No description provided."),
                    "run": module.run
                }
                logger.info(f"🧩 Skill Loaded: {metadata.get('name')} [{skill_id}]")
            else:
                logger.debug(f"Skipping {name}: Does not implement Skill Interface.")
                
        except Exception as e:
            logger.error(f"❌ Error loading skill '{name}': {e}")
            
    return registry