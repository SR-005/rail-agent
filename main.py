import os
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
    
    return create_agent(
        model=llm, tools=tools,
        system_prompt="You are Rail Agent, a helpful assistant for Indian railway queries. Use the provided tools when the user asks about train availability or tracking."
        )


if __name__=="__main__":
    agent = build_agent()
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
            cleantext="".join([block['text'] for block in reply.content if block.get('type') == 'text'])
        else:
            cleantext=str(reply.content)

        print(f"\nRail Agent: {cleantext}")
