# Description: This file contains the data models for the protocol.
from typing import Optional, List, Dict, Any


class Allocation(BaseModel):
    resource: str = ""
    hotkey: str = ""
    regkey: str = ""
    ssh_ip: str = ""
    ssh_port: int = 4444
    ssh_username: str = ""
    ssh_password: str = ""
    ssh_command: str = ""
    ssh_key: str = ""
    uuid_key: str = ""
    miner_version: int = 0


class DockerRequirement(BaseModel):
    base_image: str = "ubuntu"
    ssh_key: str = ""
    volume_path: str = "/tmp"
    dockerfile: str = ""


class UserInfo(BaseModel):
    user_id: str = ""  # wallet.hokey.ss58address
    user_pass: str = ""  # wallet.public_key hashed value
    jwt_token: str = ""  # jwt token


class ResourceGPU(BaseModel):
    gpu_name: str = ""
    gpu_capacity: int = 0
    gpu_count: int = 1


class Resource(BaseModel):
    hotkey: str = ""
    cpu_count: int = 1
    gpu_name: str = ""
    gpu_capacity: str = ""
    gpu_count: int = 1
    ram: str = "0"
    hard_disk: str = "0"
    allocate_status: str = ""  # "Avail." or "Res."


class Specs(BaseModel):
    details: str = ""


class ResourceQuery(BaseModel):
    gpu_name: Optional[str] = None
    cpu_count_min: Optional[int] = None
    cpu_count_max: Optional[int] = None
    gpu_capacity_min: Optional[float] = None
    gpu_capacity_max: Optional[float] = None
    hard_disk_total_min: Optional[float] = None
    hard_disk_total_max: Optional[float] = None
    ram_total_min: Optional[float] = None
    ram_total_max: Optional[float] = None
