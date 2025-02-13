import datetime
import os
import logging
from frcm.frcapi import METFireRiskAPI
from frcm.datamodel.model import Location
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# sample code illustrating how to use the Fire Risk Computation API (FRCAPI)
if __name__ == "__main__":
    # Check if MET_CLIENT_ID is loaded
    met_client_id = os.getenv('MET_CLIENT_ID')
    if not met_client_id:
        raise ValueError("MET_CLIENT_ID is not set. Please check your .env file.")

    frc = METFireRiskAPI()

    location = Location(latitude=60.383, longitude=5.3327)  # Bergen
    # location = Location(latitude=59.4225, longitude=5.2480)  # Haugesund

    # days into the past to retrieve observed weather data
    obs_delta = datetime.timedelta(days=2)

    try:
        wd = frc.get_weatherdata_now(location, obs_delta)
        print(wd)
    except KeyError as e:
        logging.error(f"KeyError: {e}")
        logging.error("API response did not contain expected 'data' key.")
        raise

    try:
        predictions = frc.compute_now(location, obs_delta)
        print(predictions)
    except KeyError as e:
        logging.error(f"KeyError: {e}")
        logging.error("API response did not contain expected 'data' key.")
        raise