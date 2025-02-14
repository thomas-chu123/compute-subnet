import asyncio
import websockets
import json
import uuid
import docker

# Initialize Docker client
client = docker.from_env()

class NodeManager():
    def __init__(self):
        self.client = docker.from_env()
        self.machine_uuid = None
        self.ws_url = "ws://127.0.0.1:8888"

    async def handle_action(self,action, data):
        if action == "create":
            container = client.containers.run(data["image"], detach=True)
            return {"status": "success", "container_id": container.id}
        elif action == "pause":
            container = client.containers.get(data["container_id"])
            container.pause()
            return {"status": "success"}
        elif action == "stop":
            container = client.containers.get(data["container_id"])
            container.stop()
            return {"status": "success"}
        elif action == "resume":
            container = client.containers.get(data["container_id"])
            container.unpause()
            return {"status": "success"}
        elif action == "delete":
            container = client.containers.get(data["container_id"])
            container.remove(force=True)
            return {"status": "success"}
        else:
            return {"status": "error", "message": "Unknown action"}

    async def register_machine(self,websocket):
        machine_uuid = str(uuid.uuid4())
        await websocket.send(json.dumps({"action": "register", "uuid": machine_uuid}))
        return machine_uuid

    async def main(self):
        while True:
            async with websockets.connect(self.ws_url) as websocket:
                self.machine_uuid = await self.register_machine(websocket)
                print(f"Machine registered with UUID: {self.machine_uuid}")

                async for message in websocket:
                    data = json.loads(message)
                    action = data.get("action")
                    response = await self.handle_action(action, data)
                    await websocket.send(json.dumps(response))
            await asyncio.sleep(2)

if __name__ == "__main__":
    node = NodeManager()
    asyncio.run(node.main())