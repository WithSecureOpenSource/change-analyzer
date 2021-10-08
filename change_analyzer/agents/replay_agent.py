import glob
import os
from typing import List

import gym

from change_analyzer.agents.agent import Agent
from change_analyzer.spaces.actions.app_action import AppAction
import pandas as pd
import logging


class ReplayAgent(Agent):
    def __init__(self, env: gym.Env, csv_folder: str) -> None:
        super(ReplayAgent, self).__init__(env)
        self._logger = logging.getLogger(__name__)
        self.csv_file = glob.glob(os.path.join(os.getcwd(), csv_folder, "*.csv"))[0]
        self.replay_actions = self._update_actions_from_csv()

    def run(self) -> None:
        try:
            for replay_action in self.replay_actions:
                action = self._find_action(replay_action)
                print(f"Perform action {str(action)}")
                _, _, done, _ = self.env.step(action)
                if done:
                    break
        except Exception as e:
            self._logger.info("Running failed due to an exception")
            self._logger.info(e)

    def _find_action(self, replay_action_to_find: str) -> AppAction:
        for action in self.env.action_space.actions:
            if str(action) == replay_action_to_find:
                return action

        raise Exception(f"Action {replay_action_to_find} was not found")

    def _update_actions_from_csv(self) -> List[str]:
        """Extract actions from given CSV file"""
        df = pd.read_csv(self.csv_file)

        return list(df['ActionToPerform'])
