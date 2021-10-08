import logging
import gym


class Agent:
    def __init__(self, env: gym.Env) -> None:
        self.env = env
        self.total_reward = 0.0
        self._logger = logging.getLogger(__name__)

    def run(self) -> None:
        raise NotImplementedError()
