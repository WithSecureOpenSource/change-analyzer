import glob
import os

from ludwig.api import LudwigModel
import pandas as pd
import numpy as np
import random
import json
from ast import literal_eval
import tensorflow as tf
import gym
from change_analyzer.agents.agent import Agent
from random import randrange

from PIL import Image
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from ludwig.visualize import learning_curves
import itertools
import math
import matplotlib.pyplot as plt


class ExplorerAgent(Agent):

    def __init__(self, env: gym.Env, total_steps: int = randrange(10)) -> None:
        super(ExplorerAgent, self).__init__(env)
        self.total_steps = total_steps
        self.config_file = glob.glob(os.path.join(os.getcwd()))
        print(self.config_file)
        # To avoid ValueError: tf.function-decorated function tried to create variables on non-first call'
        tf.config.run_functions_eagerly(True)

    def reward(self, image_before: np.ndarray, image_after, sequence_steps):
        """Reward function used for each performed step. Currently, a naive aproach is used."""
        # How about a Class with Rewards, for different purposes?
        penalty = 0
        if len(sequence_steps) > 2:
            # Check if the last 2 pairs of sequence steps are the same
            if sequence_steps[0:2] == sequence_steps[-3:-1]:
                print("We need to establish a penalty")
                penalty = 100000
        if image_before.size != image_after.size:
            # We are not in same window anymore
            return 0
        else:
            non_zero = np.count_nonzero(image_after - image_before)
            return non_zero - penalty

    def run(self):
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



