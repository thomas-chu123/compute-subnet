import datetime
from pymongo import MongoClient
import bittensor as bt
import os
import hashlib
# from typing import Optional
# from compute.utils.db import ComputeDb
from compute.utils.parser import ComputeArgPaser
from neurons.Validator.script import get_perf_info
import logging
from loguru import logger as logging
from logging import Handler, LogRecord

DB_IP_ADDRESS = "192.168.0.150"
DB_PORT = 27017
DB_USERNAME = "admin"
DB_PASSWORD = "mongodb"
DB_NAME = "opencompute"
DB_RUNS_NAME = "runs"
DB_LOGS_NAME = "logs"


class ComputeMongoDB:
    def __init__(self, config: bt.config, wallet: bt.wallet, role: str):

        # init the parameters
        self.config = config.copy()
        self.wallet = wallet
        self.role = os.path.splitext(role)[0]
        self.netuid = self.config.netuid
        self.hotkey = self.wallet.hotkey.ss58_address
        self.stats_count = 0

        # Create a MongoDB handler
        self.client = MongoClient(DB_IP_ADDRESS, DB_PORT, username=DB_USERNAME, password=DB_PASSWORD)
        self.db = self.client[DB_NAME]
        self.mongo_handler = MongoDBHandler(self.client, wallet.hotkey.ss58_address, config.netuid, self.role)
        logging.add(self.mongo_handler)
        bt.logging.info(f"✅ MongoDB handler created.")

        # Create a MongoDB run
        self.runs = self.db[DB_RUNS_NAME]
        self.run = {}
        self.run = self.runs.find_one({"hotkey": self.wallet.hotkey.ss58_address, "role": self.role, })
        # print(self.run)
        if self.run is None:
            if self.role == "validator":
                self.runs.insert_one({
                    "hotkey": self.wallet.hotkey.ss58_address,
                    "name": self.role + "_" + self.wallet.hotkey.ss58_address,
                    "netuid": self.config.netuid,
                    "signature": "",
                    "state": "online",
                    "role": self.role,
                    "start_time": datetime.datetime.now(datetime.timezone.utc),
                    "last_time": datetime.datetime.now(datetime.timezone.utc),
                    "duration": 0,
                    "config": {},
                    "metrics": {},
                    "stats": {},
                    "allocated_hotkeys": [],
                })

                bt.logging.info(f"✅ Validator run created in MongoDB.")
            elif self.role == "miner":
                self.run = self.runs.insert_one({
                    "hotkey": self.wallet.hotkey.ss58_address,
                    "name": self.role + "_" + self.wallet.hotkey.ss58_address,
                    "netuid": self.config.netuid,
                    "signature": "",
                    "state": "online",
                    "role": self.role,
                    "start_time": datetime.datetime.now(datetime.timezone.utc),
                    "last_time": datetime.datetime.now(datetime.timezone.utc),
                    "duration": 0,
                    "config": {},
                    "specs": {},
                    "metrics": {},
                    "stats": [],
                    "allocated": "",
                })
                bt.logging.info(f"✅ Miner run created in MongoDB.")

            self.run = self.runs.find_one(
                {"hotkey": self.wallet.hotkey.ss58_address, "role": self.role, })

        self.update_config()

    def update_config(self):
        if self.run:
            update_dict = {
                "hotkey": self.hotkey,
                "role": self.role,
                "config": self.config
            }
            self.runs.update_one({"hotkey": self.hotkey, "role": self.role, }, {"$set": update_dict})
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
        """
        You can fake these information. Do it at your own risk.
        The validators will send the number of challenges accordingly to the specifications provided here.
        So if you fake something you'll end with a very degraded score :clown:.
        Also, when your miner is allocated, the allocated user can give back a mark of reliability.
        The smaller reliability is, the faster you'll be dereg.
        """
        if self.run:
            update_dict = {
                "specs": get_perf_info(encrypted=False),
            }
            self.run['specs'] = update_dict['specs']
            self.runs.update_one({"hotkey": self.hotkey, "role": self.role}, {"$set": update_dict})

            # Sign the run
            self.sign_run()
            bt.logging.info(f"✅ Hardware details uploaded to MongoDB.")
        else:
            bt.logging.warning(f"MongoDB init failed, update specs not possible.")

    def get_miner_specs(self, queryable_uids: list):
        """
        This function gets all specs from miners.
        Only relevant for validators.
        """
        # Dictionary to store the (hotkey, specs) from mongodb runs
        db_specs_dict = {}

        try:
            # Iterate over all runs in the opencompute project
            for index, run in enumerate(self.runs.find(filter={'role': 'miner'}), start=1):
                # Access the run's configuration
                run_config = run.get('config')
                hotkey = run_config.get('hotkey')
                specs = run_config.get('specs')

                # check the signature
                if self.verify_run(run) and specs:
                    # Add the index and (hotkey, specs) tuple to the db_specs_dict if hotkey is valid
                    valid_hotkeys = [axon.hotkey for axon in queryable_uids if axon.hotkey]
                    if hotkey in valid_hotkeys:
                        db_specs_dict[index] = (hotkey, specs)

        except Exception as e:
            # Handle the exception by logging an error message
            bt.logging.error(f"An error occurred while getting specs from MongoDB: {e}")

        # Return the db_specs_dict for further use or inspection
        return db_specs_dict

    def log_chain_data(self, data: dict):
        self.runs.update_one({"hotkey": self.hotkey, "role": self.role}, {"$set": {"metrics": data}})
        self.update_last_time()
        bt.logging.info(f"✅ Chain data uploaded to MongoDB.")

    def update_stats(self, stats: dict):
        """
        This function updates the challenge stats for all miners on validator side.
        It's useless to alter this information as it's only used for data analysis.
        Not used by the validators to calculate your steak :meat:.
        """
        stats = {str(key): value for key, value in stats.items()}
        if self.run:
            self.runs.update_one({'hotkey': self.hotkey, 'role': self.role},
                                 {"$push": {'stats': stats}})
            self.stats_count += 1
            bt.logging.info(f"✅ Logging stats to MongoDB.")
        else:
            bt.logging.warning(f"mongodb init failed, logging stats not possible.")

    def update_allocated(self, allocated):
        """
        This function update the allocated value on miner side.
        It's useless to fake this information because its only used as public purpose.
        Not used by the validators to calculate your steak :meat:.
        allocated: hotkey of the validator allocating
        """
        if self.run:
            update_dict = {
                "allocated": allocated
            }
            self.run['allocated'] = allocated
            self.runs.update_one({'hotkey': self.hotkey, 'role': self.role}, {"$set": update_dict})

            # Sign the run
            self.sign_run()
        else:
            bt.logging.warning(f"mongodb init failed, update allocated not possible.")

    def update_allocated_hotkeys(self, hotkey_list: list):
        """
        This function updates the allocated hotkeys on validator side.
        It's useless to alter this information as it needs to be signed by a valid validator hotkey.
        """
        # Update the configuration with the new keys
        update_dict = {
            "allocated_hotkeys": hotkey_list
        }
        self.run['allocated_hotkeys'] = hotkey_list
        self.runs.update_one({'hotkey': self.hotkey, 'role': self.role}, {"$set": update_dict})
        # Track allocated hotkeys over time
        self.runs.update_one({'hotkey': self.hotkey, 'role': self.role}, {"$push": update_dict})

        # Sign the run
        self.sign_run()

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

    def sign_run(self):
        # Include the object run ID in the data to be signed
        data_to_sign = self.run.get("_id").__str__()

        # Compute an SHA-256 hash of the data to be signed
        data_hash = hashlib.sha256(data_to_sign.encode()).digest()

        # Sign the hash with the hotkey
        signature = self.wallet.hotkey.sign(data_hash).hex()
        update_dict = {
            "signature": signature
        }
        self.run['signature'] = signature
        self.runs.update_one({'hotkey': self.hotkey, 'role': self.role}, {"$set": update_dict})
        self.runs.update_one({'hotkey': self.hotkey, 'role': self.role}, {"$set": {"metrics": {"dummy_metric": 0}}})
        bt.logging.info(f"✅ Run signed and uploaded to MongoDB.")

    def verify_run(self, run: dict):
        # Access the run's configuration
        run_config = self.run.get('config')

        # Extract hotkey and signature from the run's summary
        hotkey = run_config.get('hotkey')
        signature = run.get('config').get('signature')  # Assuming signature is stored in summary
        run_id_str = run.get('_id').__str__()

        # Recreate the data that was signed
        data_to_sign = run_id_str

        # Compute an SHA-256 hash of the data to be signed
        data_hash = hashlib.sha256(data_to_sign.encode()).digest()

        if hotkey and signature:
            try:
                if bt.Keypair(ss58_address=hotkey).verify(data_hash, bytes.fromhex(signature)):
                    return True
                else:
                    bt.logging.info(
                        f"Run ID: {run_id_str}, Name: {run.get('name')}, Failed Signature: The signature is not valid.")
            except Exception as e:
                bt.logging.info(f"Error verifying signature for Run ID: {run_id_str}, Name: {run.get('name')}: {e}")

        return False

    def update_last_time(self):
        """
        This function updates the last time the run was updated.
        """
        time_diff = datetime.datetime.now(datetime.timezone.utc) - self.run['start_time']
        self.runs.update_one({'hotkey': self.hotkey, 'role': self.role},
                             {"$set": {'last_time': datetime.datetime.now(datetime.timezone.utc)}})
        self.runs.update_one({'hotkey': self.hotkey, 'role': self.role},
                             {"$set": {'duration': time_diff.total_seconds()}})

    def check_miner_online(self):
        """
        This function checks if the miner is online.
        """
        if self.run:
            if self.run['state'] == "online":
                return True
            else:
                return False
        else:
            return False

class MongoDBHandler(Handler):
    def __init__(self, mongo_client: MongoClient, hotkey: str, netuid: int, role: str):
        Handler.__init__(self)
        self.client = mongo_client
        self.db_log = self.client[DB_NAME][DB_LOGS_NAME]
        self.hotkey = hotkey
        self.netuid = netuid
        self.role = role
        self.db_log.insert_one({'hotkey' : self.hotkey, 'netuid': self.netuid, 'role': self.role, 'log': []})

    def emit(self, record: LogRecord):
        """
        Emit a log record to the MongoDB.
        """
        log_entry = self.format(record)
        self.db_log.update_one({'hotkey': self.hotkey, 'netuid': self.netuid, 'role': self.role},
                                   {'$push': {'log': log_entry}})

if __name__ == "__main__":
    parser = ComputeArgPaser(description="This script aims to help miners with the compute subnet.")
    config = bt.config(parser)
    wallet = bt.wallet(config=config)
    bt.logging.info(f"Wallet: {wallet}")
    # db = ComputeMongoDB(config, wallet, 'validator')
    db = ComputeMongoDB(config, wallet, 'miner')
