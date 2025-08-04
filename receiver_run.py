import logging
from receiver import Receiver

CONFIG_PATH = "./config.json"

if __name__ == "__main__":

    # Configure the logger
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    receiver_logger = logging.getLogger("ReceiverAPI")

    # Create receiver
    rc = Receiver(CONFIG_PATH, receiver_logger)

    # Run server
    rc.run()