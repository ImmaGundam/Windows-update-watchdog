import os

APP_NAME = "Windows Update Watchdog"
APP_VERSION = "1.2.1"
APP_ID = "WebGeeksIT.WindowsUpdateWatchdog"
STATUS_WINDOW_TITLE = "Watchdog Status"
APP_ICON_RELATIVE_PATH = os.path.join("assets", "icon.co")
MAX_LOG_LINES = 250
DEFAULT_GUARD_INTERVAL_SECONDS = 600
MAX_GUARD_INTERVAL_SECONDS = 12 * 60 * 60

UPDATE_SERVICES = ["wuauserv", "bits", "dosvc", "UsoSvc"]
UPDATE_OPTIONAL_SERVICES = ["WaaSMedicSvc"]

DEFENDER_CORE_SERVICE = "WinDefend"
DEFENDER_SUPPORT_SERVICES = ["WdNisSvc"]
DEFENDER_OPTIONAL_SERVICES = ["Sense"]
