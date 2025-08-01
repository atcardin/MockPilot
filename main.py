from api import Receiver
import json
from typing import Dict
import logging

def load_config(config_path: str) -> Dict:
    """Load configuration from JSON file"""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            return config
    except FileNotFoundError:
        raise
    except json.JSONDecodeError as e:
        raise
config = load_config("./endpoints.json")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

logger = logging.getLogger("ReceiverAPI")

rc = Receiver(config, logger)

rc.run()