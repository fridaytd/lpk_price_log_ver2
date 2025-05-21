from ..paths import ROOT_PATH
from .. import config

from gspread import service_account

gsheet_client = service_account(ROOT_PATH.joinpath(config.KEYS_PATH))
