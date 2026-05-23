from django.urls import re_path
from . import consumers

# This maps the WebSocket URL to our Consumer class
websocket_urlpatterns = [
    # When the browser connects to ws://localhost:8000/ws/chat/, trigger the RailAgentConsumer
    re_path(r'ws/railagentapp/$', consumers.RailAgentConsumer.as_asgi()),
]