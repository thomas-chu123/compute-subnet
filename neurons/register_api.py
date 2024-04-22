# The MIT License (MIT)
# Copyright © 2023 Crazydevlegend
# Copyright © 2023 Rapiiidooo
# Cp[yright @ 2024 Skynet
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the “Software”), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.
#
# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
# Step 1: Import necessary libraries and modules


import argparse
import base64
import os
import pyfiglet
import json
import bittensor as bt
import torch
import time


import RSAEncryption as rsa
from compute.protocol import Allocate
from compute.utils.db import ComputeDb
from compute.wandb.wandb import ComputeWandb
from neurons.Validator.database.allocate import (
    select_allocate_miners_hotkey,
    update_allocation_db,
    get_miner_details,
)
from compute.utils.version import get_local_version

from compute.utils.db import ComputeDb

from register import (
    get_config,
    get_config_cli,
    allocate_container,
    allocate_container_hotkey,
    allocate,
    allocate_hotkey,
    deallocate,
    list_allocations,
    list_resources,
    update_allocation_wandb,
)
import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

# from passlib.context import CryptContext
from pydantic import typing, BaseModel

# Database connection details
DATABASE_URL = "sqlite:///data.db"

# Security configuration
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


class Config(BaseModel):
    name: str
    description: str | None = None
    price: float
    tax: float | None = None


# Main API class
class RegisterAPI(FastAPI):
    def __init__(self):
        super().__init__()
        self.app = FastAPI()

        async def _get_conf(self):
            return {"conf": "conf"}

        # User authentication methods
        @self.app.get("/auth")
        async def _verify_password(self, username: str, plain_password: str):
            if not plain_password:
                return False
            return pwd_context.verify(plain_password, user.hashed_password)

        async def _get_current_user(self, token: str = Depends(oauth2_scheme)):
            credentials_exception = HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
            username = f"Bearer {token}"  # Extract username from token format
            is_valid = await self.verify_password(
                username, ""
            )  # Empty password for verification
            if not is_valid:
                raise credentials_exception
            return username.split()[1]  # Extract username from token format

        # @self.app.post("/login", response_model=dict)
        # # Login endpoint with token generation
        # async def _login(self, form_data: OAuth2PasswordRequestForm = Depends()):
        #     username = form_data.username
        #     password = form_data.password
        #     user = await self.verify_password(username, password)
        #     if not user:
        #         raise HTTPException(
        #             status_code=status.HTTP_400_BAD_REQUEST,
        #             detail="Incorrect username or password",
        #         )
        #     access_token = f"Bearer {username}"  # Simple token format (replace with JWT for better security)
        #     return {"access_token": access_token, "token_type": "bearer"}

        @self.app.post("/allocate_container", response_model=dict)
        async def _allocate_container(post_data: dict):
            allocate_container(config, device_requirement, timeline, public_key)
            return {"status": True, "hotkey": "hotkey", "info": "info"}

        @self.app.post("/allocate_container_hotkey", response_model=dict)
        async def _allocate_container_hotkey(
            self, config, device_requirement, timeline, public_key
        ):
            allocate_container_hotkey(config, device_requirement, timeline, public_key)
            return {"status": True, "hotkey": "hotkey", "info": "info"}

        @self.app.post("/allocate", response_model=dict)
        async def _allocate(post_data: dict):
            allocate(config, device_requirement, timeline, public_key)
            return {"status": True, "hotkey": "hotkey", "info": "info"}

        @self.app.post("/allocate_hotkey", response_model=dict)
        async def _allocate(post_data: dict):
            allocate_hotkey(config, device_requirement, timeline, public_key)
            return {"status": True, "hotkey": "hotkey", "info": "info"}

        @self.app.post("/deallocate", response_model=dict)
        async def _deallocate(
            self,
            title: str,
            description: str,
        ):
            deallocate(wandb)
            return {"status": True, "hotkey": "hotkey", "info": "info"}

        @self.app.post("/list_allocations", response_model=dict)
        async def _list_allocations(self, item_id: int):
            if not item_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Item not found"
                )
            return {"status": True}

        @self.app.post("/list_resources", response_model=dict)
        async def _list_resources(self, item_id: int):
            if not item_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Item not found"
                )
            return {"status": True}

        @self.app.post("/update_allocation_wandb", response_model=dict)
        async def _update_allocation_wandb(self, item_id: int):
            if not item_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Item not found"
                )
            return {"status": True}

    def run(self):
        uvicorn.run(self.app, host="0.0.0.0", port=9981)


# Run the FastAPI app
if __name__ == "__main__":
    api_service = RegisterAPI()
    api_service.run()
