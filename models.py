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