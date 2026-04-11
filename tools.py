import requests
from pydantic import BaseModel, Field

#declaring Models
class TrainSearchInput(BaseModel):
    fromstation: str=Field(description="The departure station name (e.g., Aluva)")
    tostation: str=Field(description="The destination station name (e.g., Bangalore)")
    date: str=Field(description="Date in DD-MM-YYYY format")



STATIONCODES={
    "aluva": "AWY",
    "ernakulam": "ERS",
    "bangalore": "SBC",
    "chennai": "MAS",
    "delhi": "NDLS",
    "trivandrum": "TVC",
    "kochi": "ERS" 
}

def availability(input: str) -> str:
    print(f"Searching train availability for: {input}")

    try:
        data=json.loads(input)
        fromcode=STATIONCODES.get(data['fromstation'].lower())
        tocode=STATIONCODES.get(data['tostation'].lower())
        date=data['date']

        if not fromcode or not tocode:
            return "Could not find Station Codes for these Stations. Please Retry with Major Stations"
        
        url=f"https://www.confirmtkt.com/itinerary-sdk/api/trains/betweenStations?fromCode={fromcode}&toCode={tocode}&date={date}"
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        response=requests.get(url,headers=headers)
        result=response.json()
        print(f"Trains: {result}")
    except Exception as e:
        print("FAILED!!")
        print(e)



def trackstatus(trainnumber: str) -> str:
    print(f"Monitoring train #{trainnumber}...")
    return (
        f"I have started the background agent to watch train {trainnumber}. "
        "I will notify you the moment a seat opens up."
    )
