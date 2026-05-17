import asyncio
import os
import subprocess
import re
import datetime
from dotenv import load_dotenv
from playwright.async_api import async_playwright

load_dotenv()

loginsession={
    "playwright": None,
    "browser": None,
    "page": None
}

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
    print(f"Searching train searchtrains for: {fromstation} to {tostation} on {date}")

    try:
        fromcode=STATIONCODES.get(fromstation.lower())
        tocode=STATIONCODES.get(tostation.lower())
        date=date
        if not fromcode or not tocode:
            return "Could not find Station Codes for these Stations. Please Retry with Major Stations"
        

        url=f"https://www.confirmtkt.com/rbooking/trains/from/{fromcode}/to/{tocode}/{date}"
        async with async_playwright() as p:

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

    async with async_playwright() as p:

        fromcode=STATIONCODES.get(fromstation.lower())
        tocode=STATIONCODES.get(tostation.lower())
        date=date
        if not fromcode or not tocode:
            return "Could not find Station Codes for these Stations. Please Retry with Major Stations"

        browser=await p.chromium.launch(headless=True) 
        context=await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page=await context.new_page()

        url=f"https://www.confirmtkt.com/rbooking/trains/from/{fromcode}/to/{tocode}/{date}"

        await page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(5)

        await page.wait_for_selector(f"#train-{trainnumber}", timeout=10000)
        traincard=page.locator(f"#train-{trainnumber}")

        seatcards=traincard.locator("div[data-key]")
        await seatcards.first.wait_for(state="visible", timeout=10000)

        coachtypes=await seatcards.count()
        results=[]
        
        for i in range(coachtypes):
            card=seatcards.nth(i)
            coachtype=await card.get_attribute("data-key") 

            cardtext=await card.inner_text()
            cleancardtext=" ".join(cardtext.split())

            if "refresh" in cleancardtext.lower():
                print(f"[System] Refreshing {coachtype}...")
                await card.click()
                await asyncio.sleep(1)

                for attempt in range(2):
                    await card.click()
                    await asyncio.sleep(1.5) 
                    try:
                        refreshlogic="""(card) => {
                            const t = card.innerText.toLowerCase();
                            const hasData = t.includes('avl') || t.includes('available') || 
                                           t.includes('wl') || t.includes('rac') || 
                                           t.includes('regret') || t.includes('not available');
                            return !t.includes('refresh') && hasData;
                        }"""
                        await page.wait_for_function(refreshlogic, arg=await card.element_handle(), timeout=15000)
                        break 
                    except:
                        print(f"[Warning] {coachtype} refresh timed out.")

                cardtext=await card.inner_text()    
                cleancardtext=" ".join(cardtext.split())

            price=re.search(r"₹\s?(\d+)", cleancardtext)
            status=re.search(r"(AVL|WL|RAC|AVAILABLE|Not Available|Regret)\s?(\d*)", cleancardtext)
            print(cleancardtext)
            
            #ticket status description
            if status!=None:
                if status.group(1)=="Regret":
                    mainstatus="Not Available"
                    message="REGRET"
                elif status.group(1)=="Not Available":
                    mainstatus="Not Available"
                    message="-"    
                elif status.group(1) in ["AVL","AVAILABLE"]:
                    mainstatus="AVAILABLE"
                elif status.group(1)=="WL":
                    mainstatus="Waiting List"
                elif status.group(1)=="RAC":
                    mainstatus="RAC"
            else:
                    mainstatus = "TICKETS NOT AVAILABLE"
                    completedstatus = "Regret"

            completedprice=f"₹{price.group(1)}" if price else "N/A"
            completedstatus=f"{mainstatus} {message if status.group(1) in ['REGRET','Not Available'] else status.group(2)}" if status else "Unknown"

            formattedresult=f"{coachtype}: {completedprice} | {completedstatus}"
            results.append(formattedresult)

        await browser.close()

    return (f"Results for {trainnumber}:\n" + "\n".join(results))

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


async def login():
    playwright=await async_playwright().start()

    print("[System] Spawning independent Chrome process...")
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    user_data_dir = r"C:\chrome_dev_profile"
    
    try:
        # DETACHED_PROCESS (0x00000008) cuts the parent-child bond on Windows
        subprocess.Popen(
            [chrome_path, "--remote-debugging-port=9222", f"--user-data-dir={user_data_dir}","--start-maximized"],
            creationflags=0x00000008 if os.name == 'nt' else 0,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        # Give Chrome a quick moment to spin up its socket server
        await asyncio.sleep(2)
    except Exception as e:
        print(f"❌ Failed to launch Chrome automatically: {e}")
        return False

    print("[System] Connecting Playwright via CDP link...")
    try:
        browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
    except Exception as e:
        print(f"❌ Connection Failed! {e}")
        return False
    
    context=browser.contexts[0]
    page=context.pages[0] if context.pages else await context.new_page()
    
    '''browser=await playwright.chromium.launch(headless=False,args=[f"--window-size=1920,1080"])
    context=await browser.new_context(no_viewport=True)
    await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    page=await context.new_page()'''



    loginsession["playwright"]=playwright
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
        await page.wait_for_selector("text=MY ACCOUNT", timeout=10000)
        print("Successfully Logged into IRCTC")
        return True
    except:
        print("Click sent, but I don't see the 'LOGOUT' button yet. Please check if a CAPTCHA appeared or if there is an error message.")
        return False

async def searchfill(fromcode: str, tocode: str, date: str, coach: str):
    page=loginsession["page"]
    print(f"[System] Filling search: {fromcode} to {tocode} for {date}")

    try:
        frominput=page.locator("#origin input")
        await frominput.fill(fromcode)
        await asyncio.sleep(1.5)
        await page.keyboard.press("Enter")

        toinput=page.locator("#destination input")
        await toinput.fill(tocode)
        await asyncio.sleep(1.5)
        await page.keyboard.press("Enter")

        dateinput=page.locator("#jDate input")
        await dateinput.click()
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await dateinput.type(date,delay=50)
        await page.keyboard.press("Tab")
        await page.keyboard.press("Tab")
        await page.keyboard.press("Tab")
        await page.keyboard.press("Enter")

        if coach!="All Classes":
            await page.click('#journeyClass')
            await page.click(f"p-dropdownitem >> text={coach}")
        
        searchbutton=page.locator("button.search_btn", has_text="Search Trains")
        await searchbutton.click(force=True)

        print("SUCCESS: Navigated to Results Page.")

        return True

    except Exception as e:
        print("Error in searchfill function ", e)
        return False

async def gettrain(trainnumber: str):
    await asyncio.sleep(3)
    page=loginsession["page"]
    print(f"[System] Getting DIV of the train #{trainnumber}")
    traincard=page.locator("app-train-avl-enq").filter(has_text=trainnumber)

    if await traincard.count()>0:
        print(f"Train DIV Found!!!")
        await traincard.scroll_into_view_if_needed()
    await asyncio.sleep(7)
    return traincard

async def gettobooking(traincard, coach: str, date: str):
    page=loginsession["page"]
    try:
        coachdiv=traincard.locator("div.pre-avl").filter(has_text=coach)
        refreshbutton=coachdiv.locator("..").locator("div.link", has_text="Refresh")
        await asyncio.sleep(4)
        if await refreshbutton.is_visible():
            print(f"[System] Refreshing {coach}...")
            await refreshbutton.click()
            await asyncio.sleep(4)

        date=datetime.datetime.strptime(date,"%d/%m/%Y")
        formatteddate=date.strftime("%d %b")
        print("Formatted Date: ",formatteddate)

        dateselector=traincard.locator("div.pre-avl").filter(has_text=formatteddate)
        if await dateselector.count()>0:
            print(f"Found the Date DIV with date {formatteddate}")
            await dateselector.first.click()
        else:
            print(f"Could not find the Date DIV with date {formatteddate}")
            return False
        
        booknowbutton=traincard.locator("button.btnDefault.train_Search", has_text="Book Now")
        await booknowbutton.wait_for(state="visible",timeout=5000)
        await booknowbutton.click()
        await asyncio.sleep(4)
        return True

    except Exception as e:
        print("Error in gettobooking function ", e)
        return False

async def passengerfill(name: str, age: str, number: str, gender: str, preference: str):
    page = loginsession["page"]
    try:
        print(f"Filling the Details of {name}, {age}, {gender}, {preference}")
        
        # Name Input
        nameinput = page.locator('p-autocomplete[formcontrolname="passengerName"] input')
        await nameinput.click()
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await nameinput.type(name, delay=100)
        await page.keyboard.press("Tab")
        await asyncio.sleep(0.5)

        # Age Input (Fixed: Click added to shift input focus)
        ageinput = page.locator('input[placeholder="Age"]')
        await ageinput.click() 
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await ageinput.type(str(age), delay=100)
        await page.keyboard.press("Tab")
        await asyncio.sleep(1)

        # Dropdowns
        await page.select_option('select[formcontrolname="passengerGender"]', label=gender)
        await page.select_option('select[formcontrolname="passengerBerthChoice"]', label=preference)
        await asyncio.sleep(1)

        # Mobile Number Input
        mobileinput = page.locator('#mobileNumber')
        await mobileinput.click()
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await mobileinput.type(number, delay=100)
        await page.keyboard.press("Tab")
        await asyncio.sleep(1)
        
        return True

    except Exception as e:
        print("Error in passengerfill function ", e)
        return False

async def initiatepayment():
    page = loginsession["page"]
    try:
        # 🟢 FIX: Use [id="3"] instead of #3 to prevent the browser syntax error
        radiobox = page.locator('p-radiobutton[id="3"]')
        
        print("[System] Scrolling to Payment Method option...")
        await radiobox.scroll_into_view_if_needed()
        
        # Click the inner widget container to guarantee the PrimeNG event fires
        print("[System] Selecting Credit/Debit/Net Banking option...")
        await radiobox.locator('.ui-radiobutton').click()
        await asyncio.sleep(1.5)

        # Locate and click the Continue button
        continue_button = page.locator("button.btnDefault.train_Search", has_text="Continue")
        await continue_button.wait_for(state="visible", timeout=5000)
        print("[System] Clicking Continue button...")
        await continue_button.click(force=True)

        # Check 1: "I Agree"
        try:
            i_agree_btn = page.locator("button", has_text="I Agree")
            await i_agree_btn.wait_for(state="visible", timeout=2000)
            await i_agree_btn.click()
            print("[System] Dismissed 'I Agree' popup.")
            await asyncio.sleep(0.5)
        except: pass

        # Check 2: Station Mismatch Accept Button ("Yes")
        try:
            yes_button = page.locator(".ui-confirmdialog-acceptbutton")
            await yes_button.wait_for(state="visible", timeout=2000)
            await yes_button.click()
            print("[System] Handled station mismatch. Clicked 'Yes'.")
            await asyncio.sleep(0.5)
        except: pass

        # Check 3: "OK" alerts
        try:
            ok_button = page.locator("button", has_text="OK")
            await ok_button.wait_for(state="visible", timeout=2000)
            await ok_button.click()
            print("[System] Dismissed 'OK' alert.")
            await asyncio.sleep(0.5)
        except: pass

        # Wait for loader to disappear
        print("[System] Monitoring the main loading layout screen...")
        try:
            loader = page.locator("div.my-loading")
            await loader.wait_for(state="hidden", timeout=95000)
            print("[System] Loading screen cleared successfully!")
            await asyncio.sleep(9)
        except Exception as e:
            print(f"[Warning] Loader tracking timed out or bypassed: {e}")

        return 0

    except Exception as e:
        print(f"Error in initiatepayment function: {e}")
        return -1

async def normalbooking(name: str, age: str,number: str, gender: str, preference: str, trainnumber: str, fromstation: str, tostation: str, date: str, coach: str):
    loginstatus=await login()
    if not loginstatus:
        print("Login Unsuccessfull!! PLEASE TRY AGAIN")
    else:
        print("Login Successfull")

    page=loginsession["page"]
    if not page:
        return "Error: No active browser session found."
    
    fromcode=STATIONCODES.get(fromstation.lower())
    tocode=STATIONCODES.get(tostation.lower())
    date=date.replace("-", "/")

    agentstatus=await searchfill(fromcode,tocode,date,coach)
    if agentstatus==False:
        return "An Error Occured- Could not get to the Search Results page of IRCTC!"

    traincard=await gettrain(trainnumber)
    getbooking=await gettobooking(traincard,coach,date)
    if getbooking==False:
        return "An Error Occured- Could not get to the Journey Booking page of IRCTC!"
    
    passengerfillstatus=await passengerfill(name,age,number,gender,preference)
    if passengerfillstatus!=True:
        return 
    
    if loginsession["browser"]:
        await loginsession["browser"].close()
    if loginsession["playwright"]:
        await loginsession["playwright"].stop()
    print("Bot exited cleanly. Over to you!")

    "An Error Occured- Could not get to the Journey Booking page of IRCTC!"
    '''print("The bot has paused. Please review the form and click 'Continue' manually.")
    await asyncio.Event().wait()'''

    #initiatepaymentstatus=await initiatepayment()



if __name__=="__main__":
    asyncio.run(normalbooking("Sreeram V Gopal","20","9020802929","Male","Lower","16127","Ernakulam","Aluva","31-05-2026","SL"))