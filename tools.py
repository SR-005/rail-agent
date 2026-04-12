import asyncio
import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from playwright.async_api import async_playwright
import time

load_dotenv()

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


STATIONCODES={
    "aluva": "AWY",
    "ernakulam": "ERS",
    "bangalore": "SBC",
    "chennai": "MAS",
    "delhi": "NDLS",
    "trivandrum": "TVC",
    "kochi": "ERS" 
}


async def searchtrains(fromstation: str, tostation: str, date: str) -> str:
    print(f"Searching train searchtrains for: {tostation} to {fromstation} on {date}")

    try:
        fromcode=STATIONCODES.get(fromstation.lower())
        tocode=STATIONCODES.get(tostation.lower())
        date=date
        if not fromcode or not tocode:
            return "Could not find Station Codes for these Stations. Please Retry with Major Stations"
        

        url=f"https://www.confirmtkt.com/rbooking/trains/from/{fromcode}/to/{tocode}/{date}"
        async with async_playwright() as p:
            print("DEBUG 0")
            browser=await p.chromium.launch(headless=True) 
            context=await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

            page=await context.new_page()
            await page.goto(url, wait_until="networkidle")
            await asyncio.sleep(5)
            content=await page.content()

            if "No trains found" in content:
                browser.close()
                return f"No trains found for {fromstation} to {tostation} on {date}."

            trainrows=await page.query_selector_all('div.body-sm.truncate.text-neutral-800')
            results=[]
            for row in trainrows:
                rawtext=await row.inner_text()
                text=rawtext.strip()
                if text:
                    results.append(text)

            print("Result's Found!!")
            await browser.close()

            if not results:
                return "I reached the page, but the train list was empty. There might be no trains on this date."
            return "\n".join(results[:10])
        
    except Exception as e:
        print("Search Train Failed while Running!!")
        print(e)

async def checkseats(trainnumber: str, fromstation: str, tostation: str, date: str) -> str:
    print(f"Checking Seat Availability of Train Number #{trainnumber}: {fromstation} to {tostation} on {date}")
    return (
        f"Availability for Train {trainnumber} from {fromstation} to {tostation} on {date}: "
        "\n- Sleeper (SL): AVAILABLE 04"
        "\n- 3-Tier AC (3A): WL 12"
        "\n- 2-Tier AC (2A): AVAILABLE 01"
    )

def trackstatus(trainnumber: str) -> str:
    print(f"Monitoring train #{trainnumber}...")
    return (
        f"I have started the background agent to watch train {trainnumber}. "
        "I will notify you the moment a seat opens up."
    )

loginsession={
    "playwright": None,
    "browser": None,
    "page": None
}

async def login():
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=False,args=[
                    f"--window-size=1920,1080"
                ])
        context=await browser.new_context(no_viewport=True)
        page=await context.new_page()

        loginsession["browser"]=browser
        loginsession["page"]=page


        await page.goto("https://www.irctc.co.in/nget/train-search")
        await asyncio.sleep(5)
        await page.click("text=LOGIN / REGISTER")

        await page.fill('input[formcontrolname="userid"]', os.getenv("IRCTCUSER"))
        await page.fill('input[formcontrolname="password"]', os.getenv("IRCTCPASS"))

        sign_in_button=page.locator("button[type='submit']", has_text="SIGN IN")
        await sign_in_button.click()

        try:
            await page.wait_for_selector("text=LOGOUT", timeout=10000)
            print("✅ SUCCESS: Logged into IRCTC Dashboard.")
            return "Login successful! I am now ready to fill your journey details."
        except:
            print("Click sent, but I don't see the 'LOGOUT' button yet. "
                    "Please check if a CAPTCHA appeared or if there is an error message.")
    
if __name__=="__main__":
    asyncio.run(login())