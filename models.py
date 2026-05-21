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

class BookingInput(BaseModel):
    name: str = Field(description="Passenger full name")
    age: str = Field(description="Passenger age")
    gender: str = Field(description="Passenger gender: Male, Female, or Transgender")
    preference: str = Field(description="Berth preference: Lower, Middle, Upper, etc.")
    trainnumber: str = Field(description="5-digit train number")
    fromstation: str = Field(description="Source station name (e.g., Ernakulam)")
    tostation: str = Field(description="Destination station name (e.g., Aluva)")
    date: str = Field(description="Travel date in DD-MM-YYYY format")
    coach: str = Field(description="Coach class (e.g., SL, 3A, 2A)")