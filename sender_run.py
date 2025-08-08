import logging
from sender import Sender

CONFIG_PATH = "./config/sender_config.yaml"

if __name__ == "__main__":

    # Configure the logger
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    logger = logging.getLogger("SenderAPI")

    # Create receiver
    sdr = Sender(CONFIG_PATH, logger)

    # Run server
    sdr.run()