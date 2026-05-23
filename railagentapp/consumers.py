import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer

class RailAgentConsumer(AsyncWebsocketConsumer):
    
    #THE HANDSHAKE
    async def connect(self):                            #This runs the exact moment a user opens the webpage
        await self.accept()
        
        # Send a welcome message directly to the browser
        await self.send(text_data=json.dumps({
            'type': 'system',
            'message': '🚂 Welcome to RailAgent UI! Connection established.'
        }))

    # 2. THE HANG UP
    async def disconnect(self, close_code):             #This runs if the user closes their browser tab.
        print(f"[System] User disconnected. Code: {close_code}")

    #THE CONVERSATION
    async def receive(self, text_data):                 #This runs every time the browser sends us a message
        textdatajson=json.loads(text_data)
        usermessage=textdatajson['message']
        
        print(f"User says: {usermessage}")

        await self.send(text_data=json.dumps({
            'type': 'status',
            'message': 'Agent is thinking...'
        }))

        try:
            await asyncio.sleep(2) 
            finaloutput=f"I received your request to: {usermessage}. (Playwright integration coming soon!)"

            await self.send(text_data=json.dumps({
                'type': 'chat',
                'message': finaloutput
            }))

        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'An error occurred: {str(e)}'
            }))