from pydantic import BaseModel

class BrandDNA(BaseModel):
    tone_of_voice: str
    target_demographic: str
    core_messaging: str
