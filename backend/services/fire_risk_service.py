import datetime

from dynamic_frcm.src.frcm.datamodel.model import FireRiskPrediction, Location
from dynamic_frcm.src.frcm.frcapi import METFireRiskAPI


class FireRiskService:
    def __init__(self):
        self.fire_risk_api = METFireRiskAPI()
        self.default_obs_delta = datetime.timedelta(days=1)

    def compute_fire_risk_now(self, location_model: Location) -> FireRiskPrediction:
        prediction = self.fire_risk_api.compute_now(location_model, obs_delta=self.default_obs_delta)
        return prediction

    def compute_fire_risk_period(self, location_model: Location, start: datetime.datetime, end: datetime.datetime) -> FireRiskPrediction:
        if end <= start:
            raise ValueError("End time must be after start time.")

        prediction = self.fire_risk_api.frc.compute_period(location_model, start=start, end=end)
        return prediction
