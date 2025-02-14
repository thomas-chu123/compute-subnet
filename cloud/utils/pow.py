# Description: This file contains the power of work (POW) class.
# POW Class
import speedtest
import psutil
import platform

class POW:
    def __init__(self):
        self.download_speed = 0
        self.upload_speed = 0
        self.disk_write_speed = 0
        self.disk_read_speed = 0
        self.computing_power = 0

    def measure_internet_speed(self):
        st = speedtest.Speedtest()
        download_speed = st.download()
        upload_speed = st.upload()
        return download_speed, upload_speed

    def measure_disk_speed(self):
        # Implement disk speed measurement
        pass

    def measure_computing_power(self):
        # Implement computing power measurement
        pass

    def check_spec(self):
        return platform.uname()
