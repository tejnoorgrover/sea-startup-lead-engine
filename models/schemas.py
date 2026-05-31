from pydantic import BaseModel, HttpUrl, Field
from typing import Optional


class StartupLead(BaseModel):
    startup_name: str
    country: str
    city: Optional[str] = None
    segment: str
    stage: Optional[str] = None
    founder_name: Optional[str] = None
    founder_title: Optional[str] = None
    business_email: Optional[str] = None
    business_phone: Optional[str] = None
    website: Optional[HttpUrl] = None
    source_url: Optional[HttpUrl] = None
    trigger: Optional[str] = None
    payment_signal: Optional[str] = None
    lead_score: int = Field(ge=0, le=100)
    priority: str
    razorpay_angle: Optional[str] = None
    data_confidence: str = "Medium"
    crm_status: str = "New"
