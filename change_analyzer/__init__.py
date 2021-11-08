__version__ = "0.10.0"

import sys

from gym.envs.registration import register


register(
    id="web-v0",
    entry_point="change_analyzer.envs:WebDriverEnv",
)
if sys.platform == 'win32':
    register(
        id="app-v0",
        entry_point="change_analyzer.envs:AppEnv",
    )
