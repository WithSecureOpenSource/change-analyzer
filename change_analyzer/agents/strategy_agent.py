import gym

from change_analyzer.agents.agent import Agent


class StrategyAgent(Agent):
    def __init__(self, env: gym.Env) -> None:
        super(StrategyAgent, self).__init__(env)

    def run(self) -> None:
        # 1. find all the screens and identify forms
        # 2. record it as a test
        # 3. reset
        # for form in forms:
        #     1. navigate to the form
        #     2. test form with invalid inputs
        #     3. record it as a test
        #     4. test form with valid inputs
        #     5. search your input on the "very next page"/"somewhere around" and make an assertion
        #     6. record it as a test
        #     7. reset
        pass
