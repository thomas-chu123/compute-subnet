import websockets
import asyncio
import logging

class WebSocketManager:
    def __init__(self, uri):
        self.uri = uri

    async def connect(self):
        async with websockets.connect(self.uri) as websocket:
            await self.handle_messages(websocket)

    async def handle_messages(self, websocket):
        async for message in websocket:
            print(f"Received message: {message}")
            # Handle task allocation, heartbeat, and notifications here

    async def send_message(self, message):
        async with websockets.connect(self.uri) as websocket:
            await websocket.send(message)
            print(f"Sent message: {message}")


    async def receive_message(self):
        async with websockets.connect(self.uri) as websocket:
            message = await websocket.recv()
            print(f"Received message: {message}")


    async def send_heartbeat(self):
        async with websockets.connect(self.uri) as websocket:
            await websocket.send("Heartbeat")
            print("Sent heartbeat")


    async def send_log(self, log):
        async with websockets.connect(self.uri) as websocket:
            await websocket.send(log)
            print(f"Sent log: {log}")


    async def upload_speed(self, upload_speed, download_speed):

        speed_data = {
            "upload_speed": upload_speed,
            "download_speed": download_speed
        }
        async with websockets.connect(self.uri) as websocket:
            await websocket.send(speed_data)
            print(f"Sent speed: {speed_data}")

    async def receive(self):
        while True:
            async with websockets.connect(self.uri) as websocket:
                async for message in websocket:
                    print(f"Received message: {message}")
                    # Handle task allocation, heartbeat, and notifications here

    async def run(self):
        while True:
            await self.connect()
            receive_task = asyncio.create_task(self.receive())
            await receive_task
            logging.debug("waiting for 2 seconds")
            await asyncio.sleep(2)

