from fastapi import FastAPI
import docker

app = FastAPI(debug=True, title="Docker API", version="1.0", log_level="trace")

from libs.allocate import register_allocation, deregister_allocation, check_allocation, check_if_allocated
from libs.container import kill_container, run_container, check_container

# Replace with your Docker host if remote
DOCKER_HOST = "tcp://192.168.122.164:2375"  # Change this to your KVM Docker host
client = docker.DockerClient(base_url=DOCKER_HOST)
# client = docker.DockerClient()


@app.get("/containers")
def list_containers():
    """List all running containers"""
    containers = client.containers.list()
    return [{"id": c.short_id, "name": c.name, "status": c.status} for c in containers]


@app.post("/containers/run")
def run_container(image: str, command: str = None):
    """Run a new container"""
    container = client.containers.run(image, command, detach=True)
    return {"id": container.short_id, "status": container.status}


@app.post("/containers/allocate")
def allocate_container():
    """Allocate a new SSH container"""
    device_requirement = {"cpu": {"count": 1}, "gpu": {
        "count": 1,
        "capacity": int(1) * 1000,
        "type": "",
    }, "hard_disk": {"capacity": 1073741824}, "ram": {"capacity": 1073741824}}

    docker_requirement = {}
    docker_requirement["base_image"] = "pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime"

    run_status = register_allocation(timeline=30,
                                     device_requirement=device_requirement,
                                     public_key="",
                                     docker_requirement=docker_requirement)
    return {"status": run_status}


@app.get("/containers/{container_id}")
def get_container_status(container_id: str):
    """Get container details"""
    try:
        container = client.containers.get(container_id)
        return {
            "id": container.short_id,
            "name": container.name,
            "status": container.status,
            "logs": container.logs().decode("utf-8"),
        }
    except docker.errors.NotFound:
        return {"error": "Container not found"}


@app.post("/containers/{container_id}/stop")
def stop_container(container_id: str):
    """Stop a running container"""
    try:
        container = client.containers.get(container_id)
        container.stop()
        return {"message": f"Container {container_id} stopped successfully"}
    except docker.errors.NotFound:
        return {"error": "Container not found"}


@app.post("/containers/{container_id}/remove")
def remove_container(container_id: str):
    """Remove a container"""
    try:
        container = client.containers.get(container_id)
        container.remove(force=True)
        return {"message": f"Container {container_id} removed successfully"}
    except docker.errors.NotFound:
        return {"error": "Container not found"}


@app.get("/images")
def list_images():
    """List available images"""
    images = client.images.list()
    return [{"id": img.short_id, "tags": img.tags} for img in images]
