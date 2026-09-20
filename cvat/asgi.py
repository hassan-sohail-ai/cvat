import os
from django.core.asgi import get_asgi_application

# Environment settings load karein
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cvat.settings.production')

# Standard Django ASGI application initialize karein
django_asgi_app = get_asgi_application()

# Aapka custom WebSocket application import karne ki koshish
try:
    from cvat.apps.test.realtime import websocket_application
except ImportError:
    websocket_application = None

async def application(scope, receive, send):
    """
    Custom ASGI application handler jo HTTP aur WebSocket dono requests ko route karta hai.
    """
    if scope['type'] == 'websocket':
        if websocket_application and scope['path'].startswith('/ws/'):
            await websocket_application(scope, receive, send)
            return
        # Agar koi aur websocket path ho jo handle nahi karna
        await send({
            'type': 'websocket.close',
            'code': 4004,
        })
        return

    # Baqi saari HTTP/REST requests ke liye standard Django ASGI app
    await django_asgi_app(scope, receive, send)