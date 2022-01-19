__version__ = "0.13.1"

import sys

from gym.envs.registration import register
from .main import run
from .sequences_diff import compare


register(
    id="web-v0",
    entry_point="change_analyzer.envs:WebDriverEnv",
)
if sys.platform == 'win32':
    register(
        id="app-v0",
        entry_point="change_analyzer.envs:AppEnv",
    )
