import os
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.tools import Tool, StructuredTool
from langchain_google_genai import ChatGoogleGenerativeAI
from tools import searchtrains, trackstatus, checkseats
from tools import TrainSearchInput, CheckSeatInput

load_dotenv()

def build_agent():
    os.getenv("GOOGLE_API_KEY")
    llm=ChatGoogleGenerativeAI(model="gemini-flash-lite-latest", temperature=0)

    #setting up tools that will be used by the agent and it's context
    tools=[
        StructuredTool.from_function(name="SearchTrains", func=None, coroutine=searchtrains,
            description=(
                "Use this tool in the following two scenarios: "
                "1. When a user mentions a departure and destination station for the first time. "
                "2. When a user explicitly changes the route, departure station, destination, or date "
                "(e.g., 'Actually, show me Kochi to Chennai' or 'Try for next Monday instead'), "
                "even if a list of trains is already visible. "
                "This tool resets the flow with new results. Do NOT use this tool if the user "
                "is selecting a train from the existing list (e.g., 'the 3rd one' or '4'); "
                "use CheckSeats for selection intent. "
                "CRITICAL: Always convert relative dates (like 'tomorrow' or 'today') "
                "into DD-MM-YYYY format before passing them to this tool."
            ),
             args_schema=TrainSearchInput),

        StructuredTool.from_function(name="CheckSeats", func=None, coroutine=checkseats,
            description=(
                "Mandatory Step 2. Use ONLY after a list is shown. "
                "INPUTS: You MUST reuse 'fromstation', 'tostation', and 'date' from the previous SearchTrains result. "
                "TRAIN NUMBER: Look at your last message. If the user said 'the second one', "
                "find the 5-digit number next to '2.' (e.g., 16349) and use that. "
                "DO NOT invent new cities or numbers."
            ),
            args_schema=CheckSeatInput),

        StructuredTool.from_function(name="TrackStatus", func=None, coroutine=trackstatus, description="Track a train number and notify when a seat opens up.")
    ]
    
    #giving context of current date to the agent
    today=datetime.now()
    tomorrow=today + timedelta(days=1)
    datecontext=f"Today is {today.strftime('%A, %d-%m-%Y')}. Tomorrow is {tomorrow.strftime('%A, %d-%m-%Y')}."

    #creating an agent
    agent=create_agent(
        model=llm, tools=tools,
        system_prompt=f"You are the 'Rail Booking Assistant', a specialized agent designed to handle the end-to-end booking process for Indian Railways. "
        f"CONTEXT: {datecontext}. "
        "\n\nGUIDELINES:"
        "\n1. GOAL: Your final goal is to complete a train booking. Treat every request as a step toward that goal."
        "\n2. SEARCH IS BOOKING: When a user says 'I want to book', do not say 'I can only search'. Instead, say 'I will find the best trains for your booking'. Immediately call SearchTrains to show options."
        "\n3. MULTI-STEP FLOW: Booking is a process: Find Train -> Select Train -> Fill Details -> Handle CAPTCHA/Payment. You are currently in the 'Finding and Selecting' phase."
        "\n4. RELATIVE DATES: Use the CONTEXT provided to resolve 'today' or 'tomorrow' into DD-MM-YYYY format before calling tools."
        "\n5. FORMATTING: Present search results as a CLEAR NUMBERED LIST (e.g., 1. [Number] [Name])."
        "\n6. NEVER use general knowledge about Indian Railways. Only use numbers and stations present in this chat history."
        "\n7. If you call CheckSeats, you are FORBIDDEN from calling SearchTrains immediately after unless the user changed the city names."
        
        "\n\nOPERATIONAL PROTOCOL:"
        "\n- PHASE 1 (Discovery): User mentions two cities -> Call SearchTrains."
        "\n- PHASE 2 (Selection): Numbered list is shown -> User picks a number -> Call CheckSeats."
        "\n- MANDATORY: Once a search is done, the cities and date are 'LOCKED'. Re-use them for CheckSeats."
        "\n- TRAIN NUMBER: The 5-digit number (e.g., 16347) is the primary key. Extract it from your own previous message."
        "\n- DATA INTEGRITY: Never invent cities like Bangalore or Delhi. Use only what the user provided."
        )
    return agent


async def main():
    agent=build_agent()
    chathistory=[]
    print("\nWELCOME TO RAIL AGENT. How can we help!?\n")
    while True:
        userinput=input("\nYou: ")

        #exit the chat loop
        if userinput.lower() in ["exit", "quit"]:
            break

        chathistory.append({"role": "user", "content": userinput})
        result=await agent.ainvoke({"messages": chathistory})
        agentreply=result['messages'][-1]
        
        #formating the output text given by LLM
        if isinstance(agentreply.content, str):
            cleantext=agentreply.content
        elif isinstance(agentreply.content, list):
            cleantext="".join([block['text'] for block in agentreply.content if block.get('type')=='text'])
        else:
            cleantext=str(agentreply.content)

        print(f"\nRail Agent: {cleantext}")
        chathistory.append(cleantext)

if __name__=="__main__":
    asyncio.run(main())