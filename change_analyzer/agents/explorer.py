from random import randrange
from typing import List

import gym
from gym import Space
from ludwig.api import LudwigModel
import numpy as np
import pandas as pd

from change_analyzer.agents.agent import Agent
from change_analyzer.spaces.actions.app_action import AppAction


class ExplorerAgent(Agent):
    def __init__(self, env: gym.Env, total_steps: int = randrange(10)) -> None:
        super(ExplorerAgent, self).__init__(env)
        self.total_steps = total_steps
        self.df = None
        self.model = None

    def run(self) -> None:
        for i in range(self.total_steps):
            try:
                action = (
                    self.env.action_space.sample()
                    if self.model is None
                    else self._predict_action(self.env.action_space.actions)
                )
                print("Perform action ", str(action))
                obs, reward, done, info = self.env.step(action)
                self.total_reward += reward

                action.df["reward"] = reward
                self._update_df(action.df)
            except Exception as e:
                self._logger.info("Action couldn't be performed due to an exception")
                self._logger.info(e)
                done = True
            if done:
                break

        self.model.train(self.df)
        self._logger.info(
            f"Episode done in {self.total_steps} steps, total reward {self.total_reward}"
        )

    def _update_df(self, df: pd.DataFrame) -> None:
        if self.df is None:
            self.df = df
            self._init_model()
            return

        self.df = pd.concat(
            [self.df, df],
            ignore_index=True,
            sort=False,
        )

    def _init_model(self):
        types = dict(self.df.dtypes)
        # TODO: map pandas to ludwig types
        config = {
            "input_features": [
                {
                    "name": col,
                    "type": types[col],
                }
                for col in self.df.columns
            ],
            "output_features": [
                {
                    "name": "reward",
                    "type": "numerical",
                }
            ],
        }
        self.model = LudwigModel(config)

    def _predict_action(self, actions: List[AppAction]) -> AppAction:
        df = pd.concat([action.df for action in actions], ignore_index=True, sort=False)
        predictions, _ = self.model.predict(df, batch_size=len(actions))
        return actions[predictions["reward"].idxmax()]  # we can try to use suboptimal action here "Epsilon-Greedy Action Selection"

