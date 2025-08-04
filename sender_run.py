import logging
from sender import Sender

CONFIG_PATH = "./config.json"

if __name__ == "__main__":

    # Configure the logger
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    receiver_logger = logging.getLogger("SenderAPI")

    # Create receiver
    sdr = Sender(CONFIG_PATH, receiver_logger)

    # Run server
    sdr.run()