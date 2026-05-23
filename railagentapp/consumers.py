import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from langchain_core.messages import HumanMessage, AIMessage
from railagentapp.main import railagent


class RailAgentConsumer(AsyncWebsocketConsumer):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chathistory = []

    #This runs the exact moment a user opens the webpage
    async def connect(self):                            
        await self.accept()
        
        # Send a welcome message directly to the browser
        await self.send(text_data=json.dumps({
            'type': 'system',
            'message': 'Welcome to RailAgent UI! Connection established.'
        }))

    #This runs if the user closes their browser tab.
    async def disconnect(self, close_code):             
        print(f"[System] User disconnected. Code: {close_code}")

    #This runs every time the browser sends us a message
    async def receive(self, text_data):                 
        textdatajson=json.loads(text_data)
        usermessage=textdatajson['message']
        
        print(f"User says: {usermessage}")

        await self.send(text_data=json.dumps({
            'type': 'status',
            'message': 'Agent is thinking...'
        }))

        try:
            self.chathistory.append(HumanMessage(content=usermessage))
            result=await railagent.ainvoke({"messages": self.chathistory})
            agentreply=result['messages'][-1]

            if isinstance(agentreply.content, str):
                cleantext = agentreply.content
            elif isinstance(agentreply.content, list):
                cleantext = "".join([block['text'] for block in agentreply.content if block.get('type')=='text'])
            else:
                cleantext = str(agentreply.content)

            self.chathistory.append(AIMessage(content=cleantext))

            await self.send(text_data=json.dumps({
                'type': 'chat',
                'message': cleantext
            }))

        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'An error occurred: {str(e)}'
            }))