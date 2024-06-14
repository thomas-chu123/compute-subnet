import datetime

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.results import (InsertOneResult, UpdateResult, DeleteResult, InsertManyResult)
from pymongo.cursor import Cursor
import bittensor as bt
import wandb
import pathlib
import os
import json
import hashlib
from typing import Optional

from dotenv import load_dotenv
from compute.utils.db import ComputeDb
from compute.utils.parser import ComputeArgPaser
from neurons.Validator.script import get_perf_info
from bson import BSON


DB_IP_ADDRESS = "192.168.0.150"
DB_PORT = 27017
DB_USERNAME = "admin"
DB_PASSWORD = "mongodb"
DB_NAME = "opencompute"
DB_RUNS_NAME = "runs"
DB_LOGS_NAME = "logs"
DB_CONFIGS_NAME = "configs"
DB_SPECS_NAME = "specs"

class ComputeMongoDB:
    def __init__(self, config: bt.config, wallet: bt.wallet, role: str):
        self.config = config.copy()

        self.client = MongoClient(DB_IP_ADDRESS, DB_PORT, username=DB_USERNAME, password=DB_PASSWORD)
        self.db = self.client[DB_NAME]
        self.runs = self.db[DB_RUNS_NAME]
        self.wallet = wallet
        self.role = os.path.splitext(role)[0]
        self.uid = self.config.uid
        self.netuid = self.config.netuid
        self.hotkey = self.wallet.hotkey.ss58_address
        self.run = self.runs.find_one({"uid": self.config.uid, "hotkey": self.wallet.hotkey.ss58_address, "role": self.role,})
        # print(self.run)
        if self.run is None:
            if self.role == "validator":
                result = self.runs.insert_one({
                    "uid": self.config.uid,
                    "hotkey": self.wallet.hotkey.ss58_address,
                    "netuid": self.config.netuid,
                    "signature": "",
                    "state": "online",
                    "role": self.role,
                    "start_time": datetime.datetime.now(datetime.timezone.utc),
                    "last_time": datetime.datetime.now(datetime.timezone.utc),
                    "duration": 0,
                    "config": {
                        "subtensor.network": self.config.subtensor.network,
                        "subtensor.chain": self.config.subtensor.chain,
                        "axon.ip": self.config.axon.ip,
                        "axon.port": self.config.axon.port,
                    },
                    "metrics": {
                        'stats': {},
                        'challenges': {},
                    },
                    "allocated_hotkeys": [],
                })

                bt.logging.info(f"✅ Validator run created in MongoDB.")
            elif self.role == "miner":
                self.run = self.runs.insert_one({
                    "uid": self.config.uid,
                    "hotkey": self.wallet.hotkey.ss58_address,
                    "netuid": self.config.netuid,
                    "signature": "",
                    "state": "online",
                    "role": self.role,
                    "start_time": datetime.datetime.now(datetime.timezone.utc),
                    "last_time": datetime.datetime.now(datetime.timezone.utc),
                    "duration": 0,
                    "config": {
                        "subtensor.network": self.config.subtensor.network,
                        "subtensor.chain": self.config.subtensor.chain,
                        "axon.ip": self.config.axon.ip,
                        "axon.port": self.config.axon.port,
                    },
                    "specs": {},
                    "metrics": {
                        'stats': {},
                        'challenges': {},
                    },
                    "chain_data": {},
                    "allocated": "",
                })
                bt.logging.info(f"✅ Miner run created in MongoDB.")

            self.run = self.runs.find_one(
                {"uid": self.config.uid, "hotkey": self.wallet.hotkey.ss58_address, "role": self.role, })

        self.update_config()

    def update_config(self):
        if self.run:
            update_dict = {
                "hotkey": self.hotkey,
                "role": self.role,
                "config": self.config
            }
            self.runs.update_one({"hotkey": self.hotkey, "role": self.role,}, {"$set": update_dict})
            # wandb.log({"dummy_metric": 0})

            # Sign the run to ensure it's from the correct hotkey
            self.sign_run()
            bt.logging.info(f"✅ Config uploaded to MongoDB.")
        else:
            bt.logging.warning(f"mongodb init failed, update config not possible.")

    def save_run_id(self, hotkey: str, run_id: str):
        pass

    def get_run_id(self, hotkey: str):
        pass

    def update_specs(self):
        if self.run:
            update_dict = {
                "specs": get_perf_info(encrypted=False),
            }
            self.runs.update_one({"hotkey": self.hotkey}, {"$set": update_dict})

            # Sign the run
            self.sign_run()

            bt.logging.info(f"✅ Hardware details uploaded to MongoDB.")
        else:
            bt.logging.warning(f"MongoDB init failed, update specs not possible.")

    def get_specs(self, hotkey: str):
        pass

    def log_chain_data (self, data: dict):
        self.runs.update_one({"hotkey": self.hotkey,}, {"$set": {"chain_data": data}})
        bt.logging.info(f"✅ Chain data uploaded to MongoDB.")

    def update_stats(self, stats: dict):
        """
        This function updates the challenge stats for all miners on validator side.
        It's useless to alter this information as it's only used for data analysis.
        Not used by the validators to calculate your steak :meat:.
        """
        stats = {str(key): value for key, value in stats.items()}
        if self.run:
            self.runs.update_one({'hotkey': self.hotkey},{"$set" : {'metrics': {"stats": stats}}})
            bt.logging.info(f"✅ Logging stats to Wandb.")
        else:
            bt.logging.warning(f"wandb init failed, logging stats not possible.")



    def update_allocated_hotkeys(self, hotkey_list: list):
        pass

    def get_allocated_hotkeys(self, valid_validator_hotkeys, flag):
        """
        This function gets all allocated hotkeys from all validators.
        Only relevant for validators.
        """
        # Query all runs in the project

        validator_runs = self.runs.find({"role": "validator"})

        # Initialize an empty list to store allocated keys from runs with a valid signature
        allocated_keys_list = []

        # Verify the signature for each validator run
        for run in validator_runs:
            try:
                # Access the run's configuration
                run_config = run.get('config')
                hotkey = run_config.get('hotkey')
                allocated_keys = run_config.get('allocated_hotkeys')

                valid_validator_hotkey = hotkey in valid_validator_hotkeys

                # Allow all validator hotkeys for data retrieval only
                if not flag:
                    valid_validator_hotkey = True

                if self.verify_run(run) and allocated_keys and valid_validator_hotkey:
                    allocated_keys_list.extend(allocated_keys)  # Add the keys to the list

            except Exception as e:
                bt.logging.info(f"Run ID: {run.id}, Name: {run.name}, Error: {e}")

        return allocated_keys_list

    def get_miner_specs(self, queryable_uids: list):
        """
        This function gets all specs from miners.
        Only relevant for validators.
        """
        # Dictionary to store the (hotkey, specs) from wandb runs
        db_specs_dict = {}

        try:
            # Iterate over all runs in the opencompute project
            for index, run in enumerate(self.runs.find(), start=1):
                # Access the run's configuration
                run_config = run.get('config')
                hotkey = run_config.get('hotkey')
                specs = run_config.get('specs')

                # check the signature
                if self.verify_run(run) and specs:
                    # Add the index and (hotkey, specs) tuple to the db_specs_dict if hotkey is valid
                    valid_hotkeys = [axon.hotkey for axon in queryable_uids.values() if axon.hotkey]
                    if hotkey in valid_hotkeys:
                        db_specs_dict[index] = (hotkey, specs)

        except Exception as e:
            # Handle the exception by logging an error message
            bt.logging.error(f"An error occurred while getting specs from wandb: {e}")

        # Return the db_specs_dict for further use or inspection
        return db_specs_dict

    def sign_run(self):
        data_to_sign = self.run.get("_id").__str__()

        # Compute a SHA-256 hash of the data to be signed
        data_hash = hashlib.sha256(data_to_sign.encode()).digest()

        # Sign the hash with the hotkey
        signature = self.wallet.hotkey.sign(data_hash).hex()
        update_dict = {
                "signature": signature
        }
        self.run['signature'] = signature
        result = self.update_doc(self.runs, self.uid, update_dict)
        self.run['metrics'] = {"dummy_metric": 0}
        bt.logging.info(f"✅ Run signed and uploaded to MongoDB.")

    def verify_run(self, run):
        pass

    @staticmethod
    def convert_dict(d: dict):
        if isinstance(d, dict):
            return {str(key): convert_dict(value) for key, value in d.items()}
        elif isinstance(d, list):
            return [convert_dict(item) for item in d]
        else:
            return d

    @staticmethod
    def insert_doc (docs: Collection, data: dict) -> InsertOneResult:
        result = docs.insert_one(data).inserted_id
        print("run_id is ", result)
        return result

    @staticmethod
    def update_doc (docs : Collection, uid: int, data: dict) -> UpdateResult:
        result = docs.update_one({'uid': uid}, {"$set": data})
        print(result)
        return result

    @staticmethod
    def remove_doc_attr (docs : Collection, data: dict, attr: dict) -> UpdateResult:
        result = docs.update_one({'uid': uid}, {"$unset": attr})
        print(result)
        return result

    @staticmethod
    def find_doc (docs: Collection, attr: dict) -> dict:
        result = docs.find_one(attr)
        print(result)
        return result

    @staticmethod
    def remove_doc (docs: Collection, data: dict) -> None:
        post = docs.delete_one(data)
        print(post)

    @staticmethod
    def count_doc (db : MongoClient, data: dict) -> None:
        user_config = db.user_config
        post = user_config.count_documents(data)
        print(post)

if __name__ == "__main__":
    parser = ComputeArgPaser(description="This script aims to help miners with the compute subnet.")
    config = bt.config(parser)
    wallet = bt.wallet(config=config)
    bt.logging.info(f"Wallet: {wallet}")
    # db = ComputeMongoDB(config, wallet, 'validator')
    db = ComputeMongoDB(config, wallet, 'miner')

