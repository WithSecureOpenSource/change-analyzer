import sys

from change_analyzer.envs.web_driver_env import WebDriverEnv
if sys.platform == 'win32':
    from change_analyzer.envs.app_env import AppEnv
