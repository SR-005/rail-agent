import asyncio
import os
import sys
import subprocess
import re
import datetime
from dotenv import load_dotenv
import smtplib
import urllib.request
import json
from email.message import EmailMessage
from playwright.async_api import async_playwright

load_dotenv()

# 🟢 Add this near the top
LAST_SEARCH_FROM = None
LAST_SEARCH_TO = None

# Ensure Windows uses the Proactor event loop so subprocess APIs work
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        # If setting the policy fails for any reason, continue without crashing
        pass

loginsession={
    "playwright": None,
    "browser": None,
    "page": None
}

STATIONCODES={
    "aluva": "AWY",
    "ernakulam south": "ERS",
    "ernakulam north": "ERN",
    "bangalore": "SBC",
    "chennai": "MAS",
    "delhi": "NDLS",
    "trivandrum": "TVC",
    "kochi": "ERS" 
}

active_trackers = {}

async def searchtrains(fromstation: str, tostation: str, date: str) -> str:
    global LAST_SEARCH_FROM, LAST_SEARCH_TO
    print(f"Searching train searchtrains for: {fromstation} to {tostation} on {date}")

    try:
        fromcode = STATIONCODES.get(fromstation.lower())
        tocode = STATIONCODES.get(tostation.lower())
        if not fromcode or not tocode:
            return "Could not find Station Codes. Please use major station names."
        
        LAST_SEARCH_FROM = fromcode
        LAST_SEARCH_TO = tocode

        url = f"https://www.confirmtkt.com/rbooking/trains/from/{fromcode}/to/{tocode}/{date}"
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            page = await context.new_page()
            
            await page.goto(url)
            print("URL: ",url)
            
            # 🟢 FIX: Wait for the specific train row container to be present in the DOM
            try:
                await page.wait_for_selector('div[id^="train-"]', timeout=15000)
            except Exception:
                await browser.close()
                return "Failed to load train list. The website might be blocking us or slow to respond."

            # Optional: Short pause to let dynamic content settle
            await asyncio.sleep(2)
            
            train_cards = await page.query_selector_all('div[id^="train-"]')
            results = []

            for card in train_cards:
                try:
                    train_id = await card.get_attribute("id")
                    train_number = train_id.replace("train-", "")
                    
                    name_el = await card.query_selector(".body-sm.text-neutral-800")
                    train_name = (await name_el.inner_text()).strip() if name_el else "Unknown Train"
                    
                    times = await card.query_selector_all('div.body-sm.text-left.font-medium')
                    dur = await card.query_selector('p.body-xs.inline-block.text-secondary')
                    stations = await card.query_selector_all('.text-sm.text-neutral-500.truncate')
                    
                    if len(times) >= 2 and dur:
                        dep = (await times[0].inner_text()).split()[0]
                        arr = (await times[1].inner_text()).split()[0]
                        d = await dur.inner_text()
                        

                        specific_from = "None"
                        specific_to = "None"
                        specific_from=(await times[0].inner_text()).split()[1]
                        specific_to=(await times[1].inner_text()).split()[1]
                            
                        print(f"{specific_from} -> {specific_to}")
                        # 🟢 Send the precise 8 fields to the AI's brain!
                        results.append(f"[TRAIN] {train_number} | {train_name} | {dep} | {arr} | {d} | {specific_from} | {specific_to}")
                except Exception as e:
                    continue

            await browser.close()

            if not results:
                return "I found the page, but no train data could be extracted."
            
            return "\n".join(results[:10])

    except Exception as e:
        print(f"Error in searchtrains: {e}")
        return "An error occurred while searching for trains."

async def checkseats(trainnumber: str, fromstation: str, tostation: str, date: str) -> str:
    print(f"Checking Seat Availability of Train Number #{trainnumber}: {fromstation} to {tostation} on {date}")

    async with async_playwright() as p:

        fromcode=fromstation
        tocode=tostation
        date=date
        if not fromcode or not tocode:
            return "Could not find Station Codes for these Stations. Please Retry with Major Stations"

        browser=await p.chromium.launch(headless=True) 
        context=await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page=await context.new_page()

        url=f"https://www.confirmtkt.com/rbooking/trains/from/{fromcode}/to/{tocode}/{date}"

        await page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(5)

        await page.wait_for_selector(f"#train-{trainnumber}", timeout=20000)
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

async def trackstatus(trainnumber: str, fromstation: str, tostation: str, date: str, coach: str, user_email: str,) -> str:
    if trainnumber in active_trackers:
        active_trackers[trainnumber].cancel()

    task=asyncio.create_task(monitorstatus(trainnumber, fromstation, tostation, date, coach, user_email))
    active_trackers[trainnumber] = task
    return (
        f"Success! I have deployed a background agent to monitor Train {trainnumber} "
        f"for {coach} class. It will check silently every 3 minutes."
    )

async def stoptracking(trainnumber: str) -> str:
    if trainnumber in active_trackers:
        active_trackers[trainnumber].cancel() # Kills the while loop!
        del active_trackers[trainnumber]
        print(f"\n[System] 🛑 Tracker for Train {trainnumber} has been manually stopped.")
        return f"Successfully stopped the background tracker for Train {trainnumber}."
    else:
        return f"I am not currently tracking Train {trainnumber}."

#threaded monitor function
async def monitorstatus(trainnumber: str, fromstation: str, tostation: str, date: str, coach: str, user_email: str,interval: int = 1) -> str:
    print(f"Background monitoring started for Train {trainnumber} ({coach}). Checking every {interval} mins...")

    while True:
        try:
            results=await checkseats(trainnumber, fromstation, tostation, date)
            resultlist=results.split('\n') if isinstance(results, str) else results
            seatfound=False
            currentstatus="Not Found"

            for line in resultlist:
                line=line.strip()
                if line.startswith(f"{coach}:"):    
                    parts=line.split("|")
                    if len(parts)>=2:
                        currentstatus=parts[1].strip().upper()
                        
                        if ("AVAILABLE" in currentstatus or "AVL" in currentstatus) and "NOT AVAILABLE" not in currentstatus:
                            seatfound=True
                    break

            if seatfound:
                print("\n"+"!!"*20)
                print(f"    SEAT ALERT: TRAIN {trainnumber} - {coach} IS {currentstatus}!")
                print("!!"*20+"\n")

                sys.stdout.write("You: ")    #for new user chat to appear
                sys.stdout.flush()
                
                send_email_alert(trainnumber, coach, currentstatus, user_email)     #send alert email

            else:
                print(f"[Tracker] Train {trainnumber} ({coach}) status: '{currentstatus}'. Sleeping for {interval} mins...")
                sys.stdout.write("You: ")    #for new user chat to appear
                sys.stdout.flush()
        except Exception as e:
            print(f"[Tracker] Error while tracking seats: {e}")

        await asyncio.sleep(interval*60)

def send_email_alert(trainnumber, coach, currentstatus, user_email):
    print("[System] Attempting to send email alert via Brevo API...")
    try:
        api_key = os.getenv("BREVO_API_KEY")
        sender_email = os.getenv("SENDER_EMAIL")

        if not api_key:
            print("[Warning] Brevo API key missing in .env file!")
            return

        url = "https://api.brevo.com/v3/smtp/email"
        
        # Build the exact JSON payload Brevo demands
        payload = {
            "sender": {"email": sender_email, "name": "Train Bot"},
            "to": [{"email": user_email}],
            "subject": f"🚨 SEAT AVAILABLE: Train {trainnumber} ({coach})",
            "textContent": f"Great news!\n\nTrain {trainnumber} for {coach} class is now showing as: {currentstatus}.\n\nGet to your computer and book it fast!"
        }

        # Convert payload to bytes and build the request headers
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='POST')
        req.add_header('accept', 'application/json')
        req.add_header('api-key', api_key)
        req.add_header('content-type', 'application/json')

        # Fire it off!
        with urllib.request.urlopen(req) as response:
            if response.status == 201:
                print("Brevo API alert sent successfully!")
            else:
                print(f"API returned status: {response.status}")

    except Exception as e:
        print(f"Failed to send Brevo API email: {e}")





#Book the Train
async def login():
    playwright=await async_playwright().start()

    print("[System] Spawning independent Chrome process...")
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    user_data_dir = r"C:\chrome_dev_profile"
    
    #opening the chrome window
    try:
        browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
        print("[System] Successfully attached to existing Chrome window!")
    except Exception:
        # If we reach here, Chrome is NOT open, so we spawn a new one.
        print("[System] Spawning NEW independent Chrome process...")
        chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        user_data_dir = r"C:\chrome_dev_profile"
        try:
            # DETACHED_PROCESS (0x00000008) cuts the parent-child bond on Windows
            subprocess.Popen(
                [chrome_path, "--remote-debugging-port=9222", f"--user-data-dir={user_data_dir}","--start-maximized",              #"--window-size=390,844"
                    #"--user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1"
                ],      
                creationflags=0x00000008 if os.name == 'nt' else 0,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            await asyncio.sleep(2)      # Give Chrome a quick moment to spin up its socket server

            try:
                browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
                await asyncio.sleep(4)
            except Exception as e:
                print(f"❌ Connection Failed! {e}")
                return False

        except Exception as e:
            print(f"❌ Failed to launch Chrome automatically: {e}")
            return False

    print("[System] Connecting Playwright via CDP link...")
    context=browser.contexts[0]
    page=context.pages[0] if context.pages else await context.new_page()

    #await page.set_viewport_size({"width": 390, "height": 844})

    loginsession["playwright"]=playwright
    loginsession["browser"]=browser
    loginsession["page"]=page

    try:
        cdp = await page.context.new_cdp_session(page)
        window_info = await cdp.send("Browser.getWindowForTarget")
        await cdp.send("Browser.setWindowBounds", {
            "windowId": window_info["windowId"],
            "bounds": {"windowState": "minimized"}
        })
        print("[System] Browser minimized. Running silently in the background...")
    except Exception as e:
        pass

    await page.goto("https://www.irctc.co.in/nget/train-search", wait_until="domcontentloaded")
    await asyncio.sleep(5)

    windowwidth=await page.evaluate("window.innerWidth")
    ismobile=windowwidth<768

    #Language Pop Up Handler
    try:
        print("[System] Checking for Language popup...")
        english_btn = page.locator("text=ENGLISH").first
        
        await english_btn.wait_for(state="visible", timeout=2000)
        await english_btn.click()
        print("[System] Successfully clicked ENGLISH!")
        
        await asyncio.sleep(1)
    except Exception:
        pass

    if ismobile:                   #for mobile cases
        try:
            print("[System] Mobile viewport detected. Opening sidebar menu...")
            hamburgermenu=page.locator(".moblogo .fa-align-justify").first
            await hamburgermenu.click(force=True)
            await asyncio.sleep(2)

            loginbutton=page.locator("button.search_btn", has_text="LOGIN / REGISTER").first
            await loginbutton.wait_for(state="attached", timeout=5000)
            await loginbutton.evaluate("node => node.click()")

        except Exception as e:
            print(f"Failed to open mobile menu: {e}")

    else:
        print("[System] Desktop viewport detected (Width: {windowwidth}px)")

        login_selector = "a:has-text('LOGIN / REGISTER')"
        await page.wait_for_selector(login_selector, timeout=15000)
        await page.click(login_selector)

    await page.fill('input[formcontrolname="userid"]', os.getenv("IRCTCUSER"))
    await page.fill('input[formcontrolname="password"]', os.getenv("IRCTCPASS"))

    sign_in_button=page.locator("button[type='submit']", has_text="SIGN IN")
    await sign_in_button.click()

    try:
        '''if ismobile:
            print("[System] Mobile viewport detected. Opening sidebar menu for Login Verification...")
            hamburgermenu=page.locator(".moblogo .fa-align-justify").first
            await hamburgermenu.click(force=True)
            await asyncio.sleep(4)

            username_label = page.locator("label:has-text('Welcome')")
            full_text = await username_label.inner_text()
            print(f"Logged text found: {full_text}")
        else:
            await page.wait_for_selector("text=MY ACCOUNT", timeout=10000)
            print("Successfully Logged into IRCTC")'''
        return True
    except:
        print("Click sent, but I don't see the 'LOGOUT' button yet. Please check if a CAPTCHA appeared or if there is an error message.")
        return False

async def searchfill(fromcode: str, tocode: str, date: str, coach: str):
    page=loginsession["page"]
    print(f"[System] Filling search: {fromcode} to {tocode} for {date}")

    try:
        frominput = page.locator("p-autocomplete#origin input")
        await frominput.click()
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await frominput.type(fromcode, delay=150)
        
        from_dropdown = page.locator(f"li[role='option']:has-text('{fromcode}')").first
        await from_dropdown.wait_for(state="visible", timeout=10000)
        await from_dropdown.click()
        await asyncio.sleep(0.5)

        toinput = page.locator("p-autocomplete#destination input")
        await toinput.click()
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await toinput.type(tocode, delay=150)
        
        to_dropdown = page.locator(f"li[role='option']:has-text('{tocode}')").first
        await to_dropdown.wait_for(state="visible", timeout=10000)
        await to_dropdown.click()
        await asyncio.sleep(0.5)

        dateinput = page.locator("p-calendar#jDate input")
        await dateinput.click()
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await dateinput.type(date, delay=100)
        await asyncio.sleep(0.5)
        await page.keyboard.press("Escape")
        await asyncio.sleep(0.5)

        if coach != "All Classes":
            await page.click('#journeyClass')
            await asyncio.sleep(0.5)
            await page.click(f"p-dropdownitem >> text={coach}")
            await asyncio.sleep(0.5)
        
        searchbutton = page.locator("button.search_btn", has_text="Search Trains")
        await searchbutton.scroll_into_view_if_needed()
        await searchbutton.click()

        await asyncio.sleep(2)
        print("SUCCESS: Navigated to Results Page.")

        return True

    except Exception as e:
        print("Error in searchfill function: ", e)
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

        #For Station Change Confirmations
        try:
            yes_button = page.locator("button", has_text="Yes").first
            await yes_button.wait_for(state="visible", timeout=3000)
            print("[System] IRCTC Station Mismatch Popup detected! Clicking 'Yes'...")
            await yes_button.click()
        except Exception:
            print("[System] No confirmation popup appeared, proceeding normally...")

        return True

    except Exception as e:
        print("Error in gettobooking function ", e)
        return False

async def passengerfill(name: str, age: str, gender: str, preference: str):
    page = loginsession["page"]

    preference=preference.strip()
    if preference.lower() in ["none", "no", "no preference", "any", "na"]:
        preference="None"
    else:
        preference=preference.title()

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

        # Age Input
        ageinput = page.locator('input[placeholder="Age"]')
        await ageinput.click() 
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await ageinput.type(str(age), delay=100)
        await page.keyboard.press("Tab")
        await asyncio.sleep(1)

        irctc_gender_code = gender.strip().upper()[0] 
        print(f"[System] DB sent '{gender}'. Sending Code '{irctc_gender_code}' to IRCTC...")
        
        genderdropdown = page.locator('select[formcontrolname="passengerGender"]')
        await genderdropdown.select_option(value=irctc_gender_code)
        await asyncio.sleep(1)

        await page.mouse.click(0, 0)
        await asyncio.sleep(0.5)
        
        #2. BERTH FIX
        if preference != "None":
            berthdropdown = page.locator('select[formcontrolname="passengerBerthChoice"]')
            await berthdropdown.click()
            await asyncio.sleep(0.5)
            try:
                clean_preference = preference.strip().title()
                await berthdropdown.select_option(label=clean_preference)
            except Exception as e:
                print(f"[Warning] Could not select Berth '{preference}'. Moving on.")
            
        for _ in range(4): 
            await page.keyboard.press("PageDown")
            await asyncio.sleep(0.4)
            
        print("[System] Ready for Payment.")
        await asyncio.sleep(2)
        
        print("[System] Executing CSS Override to reveal the Continue button...")
        await page.evaluate("""
            const btns = Array.from(document.querySelectorAll('button')).filter(b => b.innerText.includes('Continue'));
            if(btns.length > 0) {
                const btn = btns[0];
                btn.style.position = 'fixed';
                btn.style.bottom = '50px'; /* Floats it slightly above the bottom */
                btn.style.left = '5%';
                btn.style.width = '90%';
                btn.style.zIndex = '999999'; /* Forces it on top of EVERYTHING */
                btn.style.boxShadow = '0px 0px 20px red'; /* Red glow so you can't miss it */
            }
        """)

        print("[System] Ready for Payment. The Continue button has been floated for you!")
        await asyncio.sleep(2)

        continue_btn = page.locator("button:visible", has_text="Continue")
        
        if await continue_btn.count() > 0:
            await continue_btn.first.scroll_into_view_if_needed()
            print("[System] Continue button found and focused! Ready for Payment.")
        else:
            print("[System] Warning: Could not locate a visible Continue button.")
    
        await asyncio.sleep(2)
        
        return True

    except Exception as e:
        print("Error in passengerfill function ", e)
        return False

async def normalbooking(name: str, age: str, gender: str, preference: str, trainnumber: str, fromstation: str, tostation: str, date: str, coach: str, confirmed_mismatch: bool = False):
    global LAST_SEARCH_FROM, LAST_SEARCH_TO
    print(f"From Normal Booking: SEARCH{LAST_SEARCH_FROM}->{LAST_SEARCH_TO}")
    print(f"From Normal Booking: SEARCH{fromstation}->{tostation}")
    if LAST_SEARCH_FROM and LAST_SEARCH_TO:
        if fromstation != LAST_SEARCH_FROM or tostation != LAST_SEARCH_TO:
            if not confirmed_mismatch:
                print("\n[System] Tool execution BLOCKED! Forcing AI to ask for permission.")
                return (
                    f"🛑 ACTION BLOCKED: Station mismatch! The user originally searched for {LAST_SEARCH_FROM}, "
                    f"but this train departs from {fromstation.upper()}. "
                    f"You MUST ask the user: 'Warning: This train departs from {fromstation.upper()}. Proceed?' "
                    f"Do NOT run this tool again until they say YES."
                )

    loginstatus=await login()
    if not loginstatus:
        print("Login Unsuccessfull!! PLEASE TRY AGAIN")
    else:
        print("Login Successfull")

    page=loginsession["page"]
    if not page:
        return "Error: No active browser session found."
    
    fromcode = STATIONCODES.get(fromstation.lower(), fromstation).upper()
    tocode = STATIONCODES.get(tostation.lower(), tostation).upper()
    date=date.replace("-", "/")

    agentstatus=await searchfill(fromcode,tocode,date,coach)
    if agentstatus==False:
        return "An Error Occured- Could not get to the Search Results page of IRCTC!"

    traincard=await gettrain(trainnumber)
    getbooking=await gettobooking(traincard,coach,date)
    if getbooking==False:
        return "An Error Occured- Could not get to the Journey Booking page of IRCTC!"
    
    passengerfillstatus=await passengerfill(name,age,gender,preference)
    if passengerfillstatus!=True:
        return "An Error Occured while filling the passenger details."
    
    try:
        page = loginsession["page"]
        cdp = await page.context.new_cdp_session(page)
        window_info = await cdp.send("Browser.getWindowForTarget")
        
        await cdp.send("Browser.setWindowBounds", {
            "windowId": window_info["windowId"],
            "bounds": {"windowState": "normal"}
        })
        await cdp.send("Browser.setWindowBounds", {
            "windowId": window_info["windowId"],
            "bounds": {"windowState": "maximized"}
        })
        print("\n[System] Booking ready! Popping browser to the foreground for Payment...")
    except Exception as e:
        pass

    if loginsession["browser"]:
        await loginsession["browser"].close()
    if loginsession["playwright"]:
        await loginsession["playwright"].stop()

    print("\n" + "═"*50)
    print("PASSENGER DETAILS FILLED SUCCESSFULLY!")
    print("The bot has paused. Please go to the open browser and:")
    print("  1. Enter the Passenger Mobile Number.")
    print("  2. Select your Payment Method.")
    print("  3. Click 'Continue' to proceed to the CAPTCHA page.")
    print("═"*50 + "\n")

    return True






'''
async def tatkalsearchfill(fromcode: str, tocode: str, date: str, coach: str):
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

        await page.locator("#journeyQuota").click()
    
        await page.wait_for_timeout(500) 
        await page.locator("p-dropdownitem", has_text="TATKAL").first.click(force=True)
        print("[System] Quota changed to TATKAL.")

        await asyncio.sleep(3)
        
        searchbutton=page.locator("button.search_btn", has_text="Search Trains")
        await searchbutton.wait_for(state="visible", timeout=5000)
        await searchbutton.click(force=True, delay=200)

        await asyncio.sleep(3)
        print("SUCCESS: Navigated to Results Page.")

        return True

    except Exception as e:
        print("Error in searchfill function ", e)
        return False
'''

'''
async def tatkalbooking(name: str, age: str, gender: str, preference: str, trainnumber: str, fromstation: str, tostation: str, date: str, coach: str):
    try:
        journeydate=datetime.datetime.strptime(date,"%d-%m-%Y")
        bookingdate=journeydate-datetime.timedelta(days=1)

        isac = coach.upper() in ["1A", "2A", "3A", "CC", "EC", "3E", "EV"]
        openinghour = 10 if isac else 11

        targetopeningtime=bookingdate.replace(hour=openinghour,minute=0,second=0,microsecond=0)
        logintime=targetopeningtime-datetime.timedelta(minutes=2)

        now=datetime.datetime.now()
        if now<logintime:
            waitseconds=(logintime-now).total_seconds()
            print(f"\n[Tatkal Sniper] Sleeping for {int(waitseconds)} seconds. Waking up at {logintime.strftime('%I:%M %p')}...")
            await asyncio.sleep(waitseconds)
        
        print(f"\n[Tatkal Sniper] Waking up! Executing Phase 1: Login & Search...")

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

        agentstatus=await tatkalsearchfill(fromcode,tocode,date,coach)
        if agentstatus==False:
            return "An Error Occured- Could not get to the Search Results page of IRCTC!"
        
        traincard=await gettrain(trainnumber)
        now=datetime.datetime.now()
        if now<targetopeningtime:
            waitseconds=(targetopeningtime-now).total_seconds()
            print(f"[Tatkal Sniper] Ready. Waiting {waitseconds} seconds for EXACTLY {openinghour}:00:00...")
            await asyncio.sleep(waitseconds)

        
        page=loginsession["page"]

        maxretries = 15
        for attempt in range(maxretries):
            try:
                print(f"[Tatkal Sniper] Attempt {attempt}: Executing full page reload...")
                await page.reload(wait_until="domcontentloaded")
                await asyncio.sleep(2)

                getbooking=await gettobooking(traincard,coach,date)
                if getbooking==False:
                    return "An Error Occured- Could not get to the Journey Booking page of IRCTC!"
                
                passengerfillstatus=await passengerfill(name,age,gender,preference)
            except Exception as e:
                print(f"[Tatkal Sniper] Refresh attempt {attempt} failed, retrying... Error: {e}")

            return True
    except Exception as e:
            print("Error in Tatkal Booking function ", e)
            return True
    
    if passengerfillstatus!=True:
        return "An Error Occured while filling the passenger details."
    
    if loginsession["browser"]:
        await loginsession["browser"].close()
    if loginsession["playwright"]:
        await loginsession["playwright"].stop()

    print("\n" + "═"*50)
    print("🎉 PASSENGER DETAILS FILLED SUCCESSFULLY! 🎉")
    print("The bot has paused. Please go to the open browser and:")
    print("  1. Enter the Passenger Mobile Number.")
    print("  2. Select your Payment Method.")
    print("  3. Click 'Continue' to proceed to the CAPTCHA page.")
    print("═"*50 + "\n")

    return True
'''

if __name__=="__main__":
    #asyncio.run(normalbooking("Sreeram V Gopal","20","Male","Lower","16127","Ernakulam","Aluva","02-06-2026","SL"))
    asyncio.run(login())