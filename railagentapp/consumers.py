import json
from langchain_core.callbacks import BaseCallbackHandler
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from railagentapp.models import PassengerProfile 
from langchain_core.callbacks import AsyncCallbackHandler
from railagentapp.main import railagent 

class ToolStreamingCallback(AsyncCallbackHandler):
    def __init__(self, websocket):
        self.websocket = websocket

    async def on_tool_start(self, serialized: dict, input_str: str, **kwargs):
        """Fires exactly when the AI decides to use a tool."""
        tool_name = serialized.get("name", "tool")
        
        # Map your tool names to cool, user-friendly status messages
        messages = {
            "SearchTrains": "Accessing IRCTC database for train schedules",
            "CheckSeats": "Scanning live seat availability matrices",
            "TrackStatus": "Deploying background tracking daemon",
            "BookTrainTicket": "Initiating automated IRCTC booking sequence",
            "StopTracking": "Halting background tracker"
        }
        
        status_msg = messages.get(tool_name, f"Executing {tool_name}")
        
        # Send the live update to the frontend via WebSocket
        await self.websocket.send(text_data=json.dumps({
            'type': 'tool_update',
            'message': status_msg
        }))

class RailAgentConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user=self.scope["user"]

        # Reject unauthenticated users
        if self.user.is_anonymous:
            await self.close()
            return

        await self.accept()

        profiledata=await self.get_passenger_profile()
        #Inject this data as a "System Message" into this user's specific chat history
        self.chat_history=[
            {
                "role": "user", 
                "content": (
                    f"System Note: You are talking to {self.user.username}. "
                    f"Their verified email for tracking alerts is: {self.user.email}. "
                    f"Here are their strict IRCTC booking details. NEVER ask the user for these details again. "
                    f"Use these exact values when executing tools:\n{profiledata}"
                    f"Use these exact values when executing the BookTrainTicket tool:\n{profiledata}"
                )
            },
            {
                "role": "ai",
                "content": "Acknowledged. I have memorized the user's email and details and will use them automatically."
            }
        ]


    @database_sync_to_async
    def get_passenger_profile(self):
        passengers = PassengerProfile.objects.filter(user=self.user)
        
        if not passengers.exists():
            return "No passenger details saved. Ask the user to add passengers via their Profile dashboard."

        profile_list = "Here is the master list of saved passengers for this user:\n"
        for p in passengers:
            profile_list += f"- Name: {p.full_name}, Age: {p.age}, Gender: {p.gender}, Berth: {p.berth_preference}\n"
            
        profile_list += "\nIf the user says 'book it for me', use the first passenger. If they specify a name, use that specific passenger from this list."
        return profile_list

    async def receive(self, text_data):
        data = json.loads(text_data)
        usermessage=data['message']

        # Append the new message to this user's history
        self.chat_history.append({"role": "user", "content": usermessage})
        
        try:

            result = await railagent.ainvoke(
                {"messages": self.chat_history},
                config={"callbacks": [ToolStreamingCallback(self)]}
            )
            
            agentreply=result['messages'][-1]
            
            if isinstance(agentreply.content, str):
                cleantext=agentreply.content
            elif isinstance(agentreply.content, list):
                # Dig into the list and extract only the 'text' values, ignoring signatures/metadata
                cleantext="".join(
                    block["text"] for block in agentreply.content 
                    if isinstance(block, dict) and "text" in block
                )
            else:
                cleantext=str(agentreply.content)

            self.chat_history.append({"role": "ai", "content": cleantext})

            await self.send(text_data=json.dumps({
                'type': 'bot',
                'message': cleantext
            }))
            
        except Exception as e:
            print(f"Agent Error: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Sorry, my systems encountered an error while processing that.'
            }))

