import platform
import shutil
from nexus_vpn.utils.logger import log

class SystemChecker:
    @staticmethod
    def check_os():
        if platform.system() != "Linux": exit(1)
        if not (shutil.which("apt-get") or shutil.which("yum")): exit(1)
