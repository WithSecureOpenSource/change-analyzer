import uuid
from configparser import ConfigParser
from datetime import datetime
import argparse

import gym
from selenium import webdriver
from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.remote.webdriver import WebDriver

from change_analyzer.agents.random_agent import RandomAgent
from change_analyzer.agents.replay_agent import ReplayAgent
from change_analyzer.wrappers.enhanced_monitor import EnhancedMonitor
from change_analyzer.wrappers.sequence_recorder import SequenceRecorder


CONFIG = ConfigParser()


def reset() -> WebDriver:
    capabilities = DesiredCapabilities.CHROME
    if CONFIG["driver"]["platform"] == "win":
        capabilities = {
            "app": CONFIG["driver"]["app"],
            "platformName": "Windows",
            "deviceName": "WindowsPC",
        }
        driver = webdriver.Remote(CONFIG["driver"]["command_executor"], capabilities)

    if CONFIG["driver"]["platform"] == "web":
        web_options = webdriver.ChromeOptions()
        web_options.add_argument("--disable-dev-shm-usage")
        web_options.add_argument("--start-maximized")
        web_options.add_argument("--headless")
        driver = webdriver.Remote(CONFIG["driver"]["command_executor"], capabilities, options=web_options)
        driver.get(CONFIG["driver"]["url"])

    # if self.driver is not None:
    # - get another available VM and connect to it
    # - kill/reset current one

    return driver


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        help="path to config file",
        required=True,
    )
    parser.add_argument(
        "--csv_folder",
        help="path to the folder within recordings which has the targeted csv file",
        required=False,
    )
    args = parser.parse_args()
    CONFIG.read(args.config)

    env = gym.make(
        "app-v0" if CONFIG["driver"]["platform"] == "win" else "web-v0",
        reset_app=reset,
    )
    # For some reason registration sometimes doesn't work and line above can fail, direct class creation as in line
    # below could be used. See https://github.com/openai/gym/blob/master/docs/creating-environments.md for more info
    # about registration.
    # env = AppEnv(reset, {"Help"})
    sequence_id = uuid.uuid1()
    report_dir = "recordings/{}".format(datetime.now().strftime("%Y_%m_%d-%H_%M_%S"))
    # env = EnhancedMonitor(env, report_dir)
    env = SequenceRecorder(env, report_dir, sequence_id)
    try:
        env.reset()
        if args.csv_folder:
            ReplayAgent(env, args.csv_folder).run()
        else:
            RandomAgent(env, 5).run()
    finally:
        env.close()


if __name__ == "__main__":
    main()
