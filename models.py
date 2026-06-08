from pydantic import BaseModel, Field

#declaring Models
class TrainSearchInput(BaseModel):
    fromstation: str=Field(description="The departure station name (e.g., Aluva)")
    tostation: str=Field(description="The destination station name (e.g., Bangalore)")
    date: str=Field(description="Date in DD-MM-YYYY format")

class CheckSeatInput(BaseModel):
    trainnumber: str=Field(description="The 5-digit train number")
    fromstation: str=Field(description="Re-use the departure station from the search.")
    tostation: str=Field(description="Re-use the destination station from the search.")
    date: str=Field(description="Re-use the travel date from the search (DD-MM-YYYY).")

class TrackStatusInput(BaseModel):
    trainnumber: str = Field(description="The 5-digit Indian Railways train number (e.g., '16127').")
    fromstation: str = Field(description="Source station name (e.g., 'Ernakulam').")
    tostation: str = Field(description="Destination station name (e.g., 'Aluva').")
    date: str = Field(description="Travel date strictly in DD-MM-YYYY format.")
    coach: str = Field(description="Coach class (e.g., 'SL', '3A', '2A').")
    user_email: str = Field(description="The user's verified email address extracted from the system note.")

class StopTrackingInput(BaseModel):
    trainnumber: str = Field(description="The 5-digit Indian Railways train number to stop tracking.")

class BookingInput(BaseModel):
    name: str = Field(description="Passenger full name. MUST be formatted in Title Case (e.g., 'Sreeram V Gopal').")
    age: str = Field(description="Passenger age")
    gender: str = Field(description="Passenger gender: Male or Female")
    preference: str = Field(description="Berth preference: Lower, Middle, Upper, Side Lower, Side Upper etc.")
    trainnumber: str = Field(description="5-digit train number")
    fromstation: str = Field(description="Source station name (e.g., Ernakulam)")
    tostation: str = Field(description="Destination station name (e.g., Aluva)")
    date: str = Field(description="Travel date in DD-MM-YYYY format")
    coach: str = Field(description="Coach class (e.g., SL, 3A, 2A)")