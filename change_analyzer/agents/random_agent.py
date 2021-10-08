from random import randrange

import gym

from change_analyzer.agents.agent import Agent


class RandomAgent(Agent):
    def __init__(self, env: gym.Env, total_steps: int = randrange(10)) -> None:
        super(RandomAgent, self).__init__(env)
        self.total_steps = total_steps

    def run(self) -> None:
        for i in range(self.total_steps):
            # Buttons placed in the center of the screen have to be selected more often. It is possible to set higher
            # probability by calculating how far the element from the center of the screen. Or even top left quadrant
            # should be the focus area.
            try:
                action = self.env.action_space.sample()
                print("Perform action ", str(action))
                obs, reward, done, info = self.env.step(action)
                self.total_reward += reward
            except Exception as e:
                self._logger.info("Action couldn't be performed due to an exception")
                self._logger.info(e)
                done = True
            if done:
                break
        self._logger.info(
            f"Episode done in {self.total_steps} steps, total reward {self.total_reward}"
        )
