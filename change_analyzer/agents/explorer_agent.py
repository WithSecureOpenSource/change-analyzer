import glob
import os
import time

import torch
import pandas as pd
import numpy as np
import json
import gym
from typing import Tuple, List
from ludwig.api import LudwigModel
from change_analyzer.agents.agent import Agent
from random import randrange
from change_analyzer.wrappers.sequence_recorder import SequenceRecorder
from PIL import Image
from bs4 import BeautifulSoup
import math
import warnings


class ExplorerAgent(Agent):

    SEQUENCE_COLUMNS = ['Screen', 'Image', 'PageSource', 'AvailableActions']
    TARGET_DF_COLUMNS = ['ActionImage', 'ActionText', 'DistanceFromCenter', 'DistanceFromTopLeftCorner',
                         'PreviousSteps', 'ActionImageMainColorR', 'ActionImageMainColorG', 'ActionImageMainColorB']
    # ActiveScreen is removed from TARGET_DF_COLUMNS
    MODEL_DF_COLUMNS = TARGET_DF_COLUMNS + ['Reward']
    INITIAL_STEP = []  # previously ["Main view"]

    def __init__(self, env: gym.Env, total_steps: int = randrange(10)) -> None:
        super(ExplorerAgent, self).__init__(env)
        self.total_steps = total_steps
        self.config_file = glob.glob(os.path.join(os.getcwd(), 'config_ludwig_model.json'))[0]
        self.latest_recordings_folder = max(glob.glob(os.path.join('C:/projects/change-analyzer/recordings/', '*/')),
                                            key=os.path.getmtime)
        self.config = self.read_config_file()
        # Initialize needed dataframes and model
        # Sequence dataframe - a dataframe that contains what will be recorded from the current sequence
        # Target dataframe - an intermediate dataframe which will hold the available actions
        # from current screen (used to make predictions) so starting_screen is the default initialization
        # Model dataframe - a dataframe that contains new training data for the Ludwig model

        # self.sequence_df = pd.DataFrame(columns=ExplorerAgent.SEQUENCE_COLUMNS)
        self.target_df = pd.DataFrame(columns=ExplorerAgent.TARGET_DF_COLUMNS)
        self.model_df = pd.DataFrame(columns=ExplorerAgent.MODEL_DF_COLUMNS)
        self.model = None

        self.image_before = Image.new(mode='RGB', size=(0, 0))
        self.image_after = Image.new(mode='RGB', size=(0, 0))
        self.page_source_before = None
        self.page_source_after = None
        self.sequence_recorder_obj = SequenceRecorder(directory="", env=self.env, sequence_id="")
        self.previous_screen = ""
        self.sequence_steps = ExplorerAgent.INITIAL_STEP

        # To avoid ValueError: tf.function-decorated function tried to create variables on non-first call'
        # tf.config.run_functions_eagerly(True)

    def run(self) -> None:

        for i in range(self.total_steps):
            # print("Starting step", i + 1)
            try:
                action = self.get_action()
                print(f"Perform {str(action)}")
                element_to_use = str(action).replace('click on ', '')

                # Before performing the step, we need to collect the data (session may be lost once we perform the step)

                # Get image from the current screen, image_before - as numpy array
                self.image_before = Image.fromarray(self.env.render("rgb_array"))

                # Get page_source_before, using SequenceRecorder class
                self.page_source_before = self.sequence_recorder_obj.get_enriched_page_source(action.el.parent)
                # print("page_source_before within try:", self.page_source_before)

                obs, _, done, info = self.env.step(action)

                # Get available actions from current screen as list of strings
                # - we know that for a first step we always should have actions, unless something bad happened
                available_actions = [str(available_action) for available_action in self.env.action_space.actions]

                # Get image_after (already as PIL Image)
                self.image_after = obs['screenshot']

                # Get enriched page_source_after using SequenceRecorder class
                self.page_source_after = self.sequence_recorder_obj.get_enriched_page_source(action.el.parent)

                step_reward = self.reward(self.image_before, self.image_after, self.sequence_steps)

                # Update model dataframe
                print("Update model dataframe")
                self.update_model_df(available_actions=available_actions,
                                     element_to_use=element_to_use,
                                     step_reward=step_reward,
                                     sequence_steps=self.sequence_steps)
                # self.update_model_df(available_actions, element_to_use, step_reward, self.sequence_steps)

                # Update model config
                self.update_config()

                # Initialize Ludwig model
                self.init_model()

                # Train Ludwig model using model dataframe
                self.train_model()

                if len(available_actions) == 0:
                    # It means we have no available actions, and we need to quit
                    done = True

                # We can update target dataframe, now that we are sure to have available actions
                self.update_target_df(available_actions, self.sequence_steps)

            except Exception as e:
                self._logger.info("Action couldn't be performed due to an exception")
                self._logger.info(e)
                # We assume that the step failed and we are outside the SUT.
                # We need to reset the self.image_after and self.page_source_after as there is nothing after
                self.image_after = Image.new(mode='RGB', size=(0, 0))
                self.page_source_after = None

                step_reward = self.reward(self.image_before, self.image_after, self.sequence_steps)

                self.update_model_df(available_actions=[],
                                     element_to_use=element_to_use,
                                     step_reward=step_reward,
                                     sequence_steps=self.sequence_steps)  # We have no available actions
                done = True

            self.sequence_steps.append(element_to_use)

            if done:
                break

        # We need to ensure that we save the model Dataframe

        self.save_model_dataframe()
        self._logger.info(
            f"Episode done in {self.total_steps} steps, total reward {self.total_reward}"
        )

    def get_model_df(self):
        pass

    @staticmethod
    def show_pil_image(pil_image: Image):
        print("Show image")
        pil_image.show()
        time.sleep(10)

    def get_action(self):
        """
        Return the action according to the state of the model
        If the model exists, we can use it to predict the action
        If the model doesn't exist, we use a random action from the environment
        """
        if self.model:
            return self.predict_action()

        return self.env.action_space.sample()

    def predict_action(self):
        # Make predictions using targeted dataframe and current trained model
        predictions, _ = self.model.predict(self.target_df)
        print("Predictions\n", predictions)

        # Get a prediction (action with the highest reward)
        prediction_id = predictions['Reward_predictions'].idxmax()

        # Get the predicted action
        action_string = self.target_df['ActionText'][prediction_id]
        return self.env.action_space.get_action_based_on_string(action_string)

    def read_config_file(self):
        """Read the config file dedicated to Ludwig model"""
        with open(self.config_file) as config_file:
            config_content = json.load(config_file)
        return config_content

    @staticmethod
    def reward(image_before: Image, image_after: Image, sequence_steps):
        """Reward function used for each performed step. Currently, a naive aproach is used."""
        # How about a Class with Rewards, for different purposes?
        # Convert images from PIL to numpy.ndarray
        print('Calculate the step reward')
        image_before = np.array(image_before)
        image_after = np.array(image_after)
        penalty = 0
        if len(sequence_steps) > 2:
            # Check if the last 2 pairs of sequence steps are the same
            if sequence_steps[0:2] == sequence_steps[-3:-1]:
                print("We need to establish a penalty")
                penalty = 100000
        if image_before.size != image_after.size:
            # We are not in same window anymore
            print("Images don't have same size - reward 0")
            return 0
        else:
            non_zero = np.count_nonzero(image_after - image_before)
            return non_zero - penalty

    @staticmethod
    def debug_print(my_str_var):
        try:
            print(f'{my_str_var}:', {eval(my_str_var)})
        except:
            print(f'Printing {my_str_var} failed')

    def update_model_df_debug(self, available_actions: List, element_to_use: str, step_reward: int, sequence_steps: List):
        print("==== Update model dataframe ====")
        # print("Model DF before the update:\n", self.model_df)

        model_df_for_action = pd.DataFrame(
            [
                [
                    None,
                    element_to_use,
                    None,
                    None,
                    str(sequence_steps),  # previous steps
                    None,
                    None,
                    None,
                    step_reward
                ]
            ],
            columns=ExplorerAgent.MODEL_DF_COLUMNS
        )

        # self.model_df = self.model_df.append(model_df_for_action, ignore_index=True)
        # We need to have the PreviousSteps as string,
        # otherwise the list will get appended too and we will have only last sequence everywhere
        self.model_df.loc[:, "PreviousSteps"] = self.model_df.loc[:, "PreviousSteps"].astype("str")
        self.model_df = pd.concat([self.model_df, model_df_for_action], ignore_index=True)
        print("==== Model DF updated ====")
        # print("Model DF after the update:\n", self.model_df)

    def update_model_df(self, available_actions: list, element_to_use: str, step_reward: int, sequence_steps: List):
        """Create model_df for performed action
        The Dataframe consists of:
            - 'ActionImage': the image of the performed action (for instance the image of a button)
            - 'ActionText': the string representing the action (for instance "Status details") - element_to_use
            - 'DistanceFromCenter': distance from the center of action image in the previous screen
            - 'DistanceFromTopLeftCorner': distance from top-left corner of action image in the previous screen
            - 'ActiveScreen': the previous screen # TODO refactor to previous_screen_text | removed for now
            - 'PreviousSteps': the list of previous steps (self.sequence_steps)
            - 'ActionImageMainColorR': red from main color of the action image
            - 'ActionImageMainColorG': green from main color of the action image
            - 'ActionImageMainColorB: blue from main color of the action image
            - 'Reward': the reward received by performing the action (step_reward)
        """

        # self.debug_print('self.page_source_before')
        # self.debug_print('self.active_screen')
        # self.debug_print('self.image_before')

        # Get ActionImage
        # First we need the coordinates for the action image, from self.page_source_before
        action_coordinates = self.get_action_coords(self.page_source_before, element_to_use)

        # Use coordinates to extract the action image from previous screen, self.image_before
        # Originally action_img was numpy.ndarray.
        # Due to migration of Ludwig to 0.5, it has to be converted to a tensor
        action_img = self.get_action_image(self.image_before, action_coordinates)
        print('Action img num of channels:', action_img.shape, len(action_img.shape))
        action_img_tensor = torch.from_numpy(self.get_action_image(self.image_before,
                                                                   action_coordinates)).permute(2, 0, 1)

        # Get DistanceFromCenter
        distance_from_center = self.get_distance_from_center(action_coordinates, self.image_before)

        # GetDistanceFromTopLeftCorner
        distance_from_top_left_corner = self.get_distance_from_top_left_corner(action_coordinates)

        # Get ActiveScreen
        # active_screen_text = self.sequence_steps[-1]  # The screen the action originates from

        # Get RGB from main color of the action_image
        r, g, b = self.get_main_color_from_action_image(action_img)

        model_df_for_action = pd.DataFrame(
            [
                [
                    action_img_tensor,
                    element_to_use,
                    distance_from_center,
                    distance_from_top_left_corner,
                    # active_screen_text,
                    str(sequence_steps),  # previous steps
                    r,
                    g,
                    b,
                    step_reward
                ]
            ],
            columns=ExplorerAgent.MODEL_DF_COLUMNS
        )

        self.model_df.loc[:, "PreviousSteps"] = self.model_df.loc[:, "PreviousSteps"].astype("str")

        self.model_df = self.model_df.append(model_df_for_action, ignore_index=True)

    @staticmethod
    def get_main_color_from_action_image(action_image):
        # print('Get main color')
        # Convert from numpy array to PIL image
        action_image = Image.fromarray(action_image)
        max_colors = action_image.width * action_image.height
        colors = action_image.getcolors(max_colors)
        return colors[0][1]

    @staticmethod
    def get_action_image(screen_img: Image, action_coordinates: Tuple):
        """Get action image from given screen image, based on coordinates"""
        x = action_coordinates[0]
        y = action_coordinates[1]
        h = action_coordinates[2]
        w = action_coordinates[3]
        action_img = screen_img.crop((x, y, x + w, y + h))
        # Let's return a numpy array
        return np.asarray(action_img)

    @staticmethod
    def get_action_coords(page_source: str, action: str):
        """Find action within the Screen page source"""
        soup = BeautifulSoup(page_source, "html.parser")

        el = soup.find(attrs={'name': action})

        if el is None:
            # If we couldn't find anything by name attribute, we use helptext
            # Would be good to be more generic, to use a list of attributes that could find the action
            el = soup.find(attrs={'helptext': action})

        x = int(el['x'])
        y = int(el['y'])
        h = int(el['height'])
        w = int(el['width'])

        return x, y, h, w

    @staticmethod
    def get_distance_from_center(action_coordinates, screen_img):
        """The distance is calculated between the center of the action image and the center of the screen image
        x1, y1 are the coordinates within screen image of action image's center
        x2, y2 are the coordinates of the screen image's center
        Formula to calculate the distance between two points A(x1,y1) and B(x2,y2) is:
        d = √((x1-x2)^2 + (y1-y2)^2)
        """
        x1 = action_coordinates[0]
        y1 = action_coordinates[1]
        x2 = screen_img.size[0] / 2
        y2 = screen_img.size[1] / 2

        return int(math.sqrt(math.pow(x1 - x2, 2) + math.pow(y1 - y2, 2)))

    @staticmethod
    def get_distance_from_top_left_corner(action_coordinates):
        """The distance is calculated between the center of the action image and the top left corner of the screen image
        x1, y1 are the coordinates within screen image of action image's center
        x2, y2 are the coordinates of the screen image's top left corner which in this case are 0 and 0
        Formula to calculate the distance between two points A(x1,0) and B(x2,0) is:
        d = √(x1^2 + y1^2)
        """
        x1 = action_coordinates[0]
        y1 = action_coordinates[1]

        return int(math.sqrt(math.pow(x1, 2) + math.pow(y1, 2)))

    @staticmethod
    def get_max_dims(images):
        max_w = 0
        max_h = 0

        for image in images:
            max_w = max(image.size[0], max_w)
            max_h = max(image.size[1], max_h)

        return max_h, max_w

    def update_config(self):
        print("Update model config")
        # Get all action images from model_df as PIL images
        # Actions images are now torch tensors and here are converted to numpy arrays
        # Permute tensor channels back from 2,0,1 to 1,2,0
        action_images = [Image.fromarray(action_image.permute(1, 2, 0).numpy()) for action_image in self.model_df['ActionImage'].tolist()]

        # Find the maximum height and width from images
        max_h, max_w = self.get_max_dims(action_images)

        # Update config preprocessing section with new height and width
        self.config['input_features'][0]['preprocessing']['height'] = max_h
        self.config['input_features'][0]['preprocessing']['width'] = max_w

    def update_target_df(self, available_actions, seq_steps):
        """
        Create Target Dataframe, used for next step prediction
        The Dataframe consists of:
            - 'ActionImage': the images of the available images from active screen (for instance images of a button)
            - 'ActionText': the string representing the action associated with 'ActionImage'
            - 'DistanceFromCenter': distance from the center of 'ActionImage' in active screen
            - 'DistanceFromTopLeftCorner': distance from top-left corner of 'ActionImage' in active screen
            - 'ActiveScreen': the text of active screen | removed for now
            - 'PreviousSteps': the list of previous steps (self.sequence_steps)
            - 'ActionImageMainColorR': red from main color of the 'ActionImage'
            - 'ActionImageMainColorG': green from main color of the 'ActionImage'
            - 'ActionImageMainColorB: blue from main color of the 'ActionImage'
        """
        print("Create target_df for Ludwig model")

        # Get future screens from AvailableActions -> in func param
        # We need to convert all available_actions from 'click on <action>' to '<action>'
        available_actions = [str(action).replace('click on ', '') for action in available_actions]

        # print('Available actions:', available_actions)
        # available_actions = current_action_df['AvailableActions'].iloc[0]

        # Get ActiveScreen -> self.active_screen
        # print("Get ActiveScreen:", self.active_screen)
        # active_screen = current_action_df['Screen'].iloc[0]

        # Get distances
        distances_from_center = []
        distances_from_top_left_center = []

        # active_Screen_image is in fact self.image_after
        for action in available_actions:
            action_coords = self.get_action_coords(self.page_source_after, action)
            distances_from_center.append(self.get_distance_from_center(action_coords, self.image_after))
            distances_from_top_left_center.append(self.get_distance_from_top_left_corner(action_coords))

        # print(f"Distances\nFrom center: {distances_from_center} \nFrom top-left: {distances_from_top_left_center}")

        action_images = self.get_actions_images_from_screen(self.image_after, self.page_source_after, available_actions)

        # print(action_images)
        main_color_rs = []
        main_color_gs = []
        main_color_bs = []
        for action_image in action_images:
            # r, g, b = self.get_main_color_from_action_image(Image.fromarray(action_image))
            # action_image is converted to Image.fromarray (numpy.ndarray) within get_main_color function
            r, g, b = self.get_main_color_from_action_image(action_image)
            main_color_rs.append(r)
            main_color_gs.append(g)
            main_color_bs.append(b)

        # print(f"Main RGBs for action images \nRs: {main_color_rs} \nBs: {main_color_bs} \nGs: {main_color_gs}")

        # Create data for target_df
        target_data = {
            'ActionImage': action_images,
            'ActionText': available_actions,
            'DistanceFromCenter': distances_from_center,
            'DistanceFromTopLeftCorner': distances_from_top_left_center,
            # 'ActiveScreen': [self.active_screen for a in available_actions],
            'PreviousSteps': [', '.join(map(str, seq_steps)) for a in available_actions],
            # 'PreviousSteps': [', '.join(map(str, self.sequence_steps)) for a in available_actions],
            'ActionImageMainColorR': main_color_rs,
            'ActionImageMainColorG': main_color_gs,
            'ActionImageMainColorB': main_color_bs,
        }

        self.target_df = pd.DataFrame(target_data)

    def get_actions_images_from_screen(self, screen_image, page_source, actions):
        """Get all actions images (PIL -> numpy array) from given screen as a list"""
        images = []
        for action in actions:
            action_coords = self.get_action_coords(page_source, action)
            images.append(np.array(self.get_action_image(screen_image, action_coords)))

        return images

    def init_model(self):
        print("Initialize Ludwig model")
        self.model = LudwigModel(self.config)
        print('Model initialized')

    def train_model(self):
        # print("Model Dataframe", self.model_df)
        print('Train model')
        train_stats, _, _ = self.model.train(self.model_df)
        print('Model trained')

    def save_model_dataframe(self) -> None:
        """Save model dataframe, to be used later on in future models"""
        print("Save the model dataframe")
        csv_file = os.path.join(self.latest_recordings_folder, 'model_df.csv')
        self.model_df.to_csv(csv_file, index=False)
