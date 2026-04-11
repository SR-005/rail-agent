import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.tools import Tool, StructuredTool
from langchain_google_genai import ChatGoogleGenerativeAI
from tools import availability, trackstatus, TrainSearchInput

load_dotenv()

def build_agent():
    os.getenv("GOOGLE_API_KEY")
    llm=ChatGoogleGenerativeAI(model="gemini-flash-lite-latest", temperature=0)

    tools=[
        StructuredTool.from_function(name="SearchTrains", func=availability, description="Find train availability between two stations on a given date.",
             args_schema=TrainSearchInput),
        StructuredTool.from_function(name="TrackStatus", func=trackstatus, description="Track a train number and notify when a seat opens up.")
    ]
    
    today=datetime.now()
    tomorrow=today + timedelta(days=1)
    datecontext=f"Today is {today.strftime('%A, %d-%m-%Y')}. Tomorrow is {tomorrow.strftime('%A, %d-%m-%Y')}."

    return create_agent(
        model=llm, tools=tools,
        system_prompt=f"You are the 'Rail Booking Assistant', a specialized agent designed to handle the end-to-end booking process for Indian Railways. "
        f"CONTEXT: {datecontext}. "
        "\n\nGUIDELINES:"
        "\n1. GOAL: Your final goal is to complete a train booking. Treat every request as a step toward that goal."
        "\n2. SEARCH IS BOOKING: When a user says 'I want to book', do not say 'I can only search'. Instead, say 'I will find the best trains for your booking'. Immediately call SearchTrains to show options."
        "\n3. MULTI-STEP FLOW: Booking is a process: Find Train -> Select Train -> Fill Details -> Handle CAPTCHA/Payment. You are currently in the 'Finding and Selecting' phase."
        "\n4. RELATIVE DATES: Use the CONTEXT provided to resolve 'today' or 'tomorrow' into DD-MM-YYYY format before calling tools."
        "\n5. PERSISTENCE: If a train is full, suggest using 'TrackStatus' as a background monitoring agent to catch a seat for the booking."
        )


if __name__=="__main__":
    agent=build_agent()
    print("\nWELCOME TO RAIL AGENT. How can we help!?\n")
    while True:
        userinput=input("\nYou: ")

        #exit the chat loop
        if userinput.lower() in ["exit", "quit"]:
            break
        result=agent.invoke({"messages": [{"role": "user", "content": userinput}]})
        reply=result['messages'][-1]
        
        #formating the output text given by LLM
        if isinstance(reply.content, str):
            cleantext=reply.content
        elif isinstance(reply.content, list):
            cleantext="".join([block['text'] for block in reply.content if block.get('type')=='text'])
        else:
            cleantext=str(reply.content)

        print(f"\nRail Agent: {cleantext}")
