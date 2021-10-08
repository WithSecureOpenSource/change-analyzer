import os
from os.path import isfile
from typing import Dict, Tuple
import pandas as pd
import time
import json

import gym as gym
from gym import Wrapper
from selenium.webdriver.remote.webdriver import WebDriver

from change_analyzer.spaces.actions.app_action import AppAction
from change_analyzer.wrappers.transparent_wrapper_mixin import TransparentWrapperMixin


class SequenceRecorder(Wrapper, TransparentWrapperMixin):
    COL_TIMESTAMP = 'Timestamp'
    COL_SEQUENCE_ID = 'SequenceId'
    COL_PAGE_SOURCE_BEFORE = 'PageSourceBefore'
    COL_PAGE_SOURCE_AFTER = 'PageSourceAfter'
    COL_ACTION_TO_PERFORM = 'ActionToPerform'
    COL_ACTION_IMAGE_BEFORE = 'ActionImageBefore'
    COL_ACTION_IMAGE_AFTER = 'ActionImageAfter'

    def __init__(self, env: gym.Env, directory: str, sequence_id: str) -> None:
        super(SequenceRecorder, self).__init__(env)
        self._sequence_id = sequence_id
        os.makedirs(directory, exist_ok=True)
        self._csv_file = f"{directory}/{sequence_id}.csv"

    def step(self, action: AppAction) -> Tuple[Dict, float, bool, WebDriver]:
        current_action = str(action)
        page_source_before = action.el.parent.page_source
        page_source_after = ""
        image_before = []
        image_after = []
        try:
            image_before = self.env.render("rgb_array").tolist()
            obs, reward, done, info = self.env.step(action)
            image_after = self.env.render("rgb_array").tolist()
            page_source_after = info.page_source
        finally:
            self._save_dataframe_to_csv(pd.DataFrame({
                self.COL_TIMESTAMP: [int(time.time())],
                self.COL_SEQUENCE_ID: [self._sequence_id],
                self.COL_PAGE_SOURCE_BEFORE: [page_source_before],
                self.COL_PAGE_SOURCE_AFTER: [page_source_after],
                self.COL_ACTION_TO_PERFORM: [current_action],
                self.COL_ACTION_IMAGE_BEFORE: [json.dumps(image_before)],
                self.COL_ACTION_IMAGE_AFTER: [json.dumps(image_after)],
            }))
        return obs, reward, done, info

    def close(self) -> None:
        self.env.close()

    def _save_dataframe_to_csv(self, df: pd.DataFrame) -> None:
        if isfile(self._csv_file):  # it exists so append without writing the header
            df.to_csv(self._csv_file, index=False, mode='a', header=False)
        else:
            df.to_csv(self._csv_file, index=False)