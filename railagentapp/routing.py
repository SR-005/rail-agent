from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/railagentapp/$', consumers.RailAgentConsumer.as_asgi()),
]