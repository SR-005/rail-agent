import json
import requests
from pydantic import BaseModel, Field
from playwright.sync_api import sync_playwright
import time

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



def availability(fromstation: str, tostation: str, date: str) -> str:
    print(f"Searching train availability for: {tostation} to {fromstation} on {date}")

    try:
        fromcode=STATIONCODES.get(fromstation.lower())
        tocode=STATIONCODES.get(tostation.lower())
        date=date

        if not fromcode or not tocode:
            return "Could not find Station Codes for these Stations. Please Retry with Major Stations"
        

        url=f"https://www.confirmtkt.com/rbooking/trains/from/{fromcode}/to/{tocode}/{date}"

        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True) 
            context=browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            page=context.new_page()

            page.goto(url, wait_until="networkidle")
            time.sleep(4)
            content=page.content()

            if "No trains found" in content:
                browser.close()
                return f"No trains found for {fromstation} to {tostation} on {date}."
            
            train_rows=page.query_selector_all('div.body-sm.truncate.text-neutral-800')
            
            results=[]
            for row in train_rows:
                text=row.inner_text().strip()
                if text:
                    results.append(text)

            print(f"Found: {results}")
            browser.close()

            if not results:
                return "I reached the page, but the train list was empty. There might be no trains on this date."
            return f"I found these trains: {', '.join(results[:5])}"
        
    except Exception as e:
        print("FAILED!!")
        print(e)



def trackstatus(trainnumber: str) -> str:
    print(f"Monitoring train #{trainnumber}...")
    return (
        f"I have started the background agent to watch train {trainnumber}. "
        "I will notify you the moment a seat opens up."
    )
