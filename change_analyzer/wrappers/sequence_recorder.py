import os
from os.path import isfile
from typing import Dict, Tuple, List
import pandas as pd
import time
import json

import gym as gym
from gym import Wrapper
from selenium.webdriver.remote.webdriver import WebDriver
from lxml import html

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
    COL_PAGE_ELEMENTS_AFTER = 'PageElementsAfter'
    COL_PAGE_ELEMENTS_BEFORE = 'PageElementsBefore'

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
        page_elements_after = []
        page_elements_before = []
        if 'html' in page_source_before:
            page_elements_before.append(self.get_all_elements_from_webpage(info=action.el.parent))

        try:
            image_before = self.env.render("rgb_array").tolist()
            obs, reward, done, info = self.env.step(action)
            image_after = self.env.render("rgb_array").tolist()
            page_source_after = info.page_source
            if 'html' in page_source_after:
                page_elements_after.append(self.get_all_elements_from_webpage(info))
        finally:
            self._save_dataframe_to_csv(pd.DataFrame({
                self.COL_TIMESTAMP: [int(time.time())],
                self.COL_SEQUENCE_ID: [self._sequence_id],
                self.COL_PAGE_SOURCE_BEFORE: [page_source_before],
                self.COL_PAGE_SOURCE_AFTER: [page_source_after],
                self.COL_ACTION_TO_PERFORM: [current_action],
                self.COL_ACTION_IMAGE_BEFORE: [json.dumps(image_before)],
                self.COL_ACTION_IMAGE_AFTER: [json.dumps(image_after)],
                self.COL_PAGE_ELEMENTS_AFTER: [page_elements_after],
                self.COL_PAGE_ELEMENTS_BEFORE: [page_elements_before],
            }))
        return obs, reward, done, info

    @staticmethod
    def get_all_elements_from_webpage(info: WebDriver) -> List[Tuple]:
        """Get all elements of a given page, defined by the info's page_source.
        All elements will have the following data:
            - Full xpath
            - Text if available
            - x, y coordinates
            - h, w dimensions
        """
        page_elements = []

        # Get elements' xpaths from given page source
        page_elements_xpaths = []
        root = html.fromstring(info.page_source)
        tree = root.getroottree()
        all_elements_by_xpath = root.xpath('//*')
        for element in all_elements_by_xpath:
            page_elements_xpaths.append(tree.getpath(element))

        # Get other data using the info driver
        all_driver_elements = info.find_elements_by_xpath("//*")
        for i, el in enumerate(all_driver_elements):
            page_elements.append((page_elements_xpaths[i], el.text, el.location, el.size))

        return page_elements

    def close(self) -> None:
        self.env.close()

    def _save_dataframe_to_csv(self, df: pd.DataFrame) -> None:
        if isfile(self._csv_file):  # it exists so append without writing the header
            df.to_csv(self._csv_file, index=False, mode='a', header=False)
        else:
            df.to_csv(self._csv_file, index=False)
