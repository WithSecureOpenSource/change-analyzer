import os
from os.path import isfile
from typing import Dict, Tuple
import pandas as pd
import time
import json

import gym as gym
import selenium.webdriver.remote.webelement
from gym import Wrapper
from selenium.webdriver.remote.webdriver import WebDriver, WebElement
from lxml import html, etree

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
        # The ifs regarding sequence_id and directory are in place, to allow independent access to sequence_recorder
        # functions, for example to get enriched page_source within Explorer agent - therefore we can have empty strings
        if sequence_id:
            self._sequence_id = sequence_id
        if directory:
            os.makedirs(directory, exist_ok=True)
            self._csv_file = f"{directory}/{sequence_id}.csv"

    def step(self, action: AppAction) -> Tuple[Dict, float, bool, WebDriver]:
        current_action = str(action)
        page_source_before = self.get_enriched_page_source(info=action.el.parent)
        page_source_after = ""
        image_before = []
        image_after = []

        try:
            if not isfile(self._csv_file):
                # We are executing first step and only now we store image_before
                image_before = self.env.render("rgb_array").tolist()
            obs, reward, done, info = self.env.step(action)
            image_after = self.env.render("rgb_array").tolist()
            page_source_after = self.get_enriched_page_source(info)
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

    @staticmethod
    def _enrich_element(element_to_enrich: html.HtmlElement, element_info: Dict):
        element_to_enrich.set('x', str(element_info['x']))
        element_to_enrich.set('y', str(element_info['y']))
        element_to_enrich.set('height', str(element_info['height']))
        element_to_enrich.set('width', str(element_info['width']))

    def get_enriched_page_source(self, info: WebDriver) -> str:
        """Enrich a given page source with additional info from the WebDriver
        All page elements will have the following additional info:
            - Text if available
            - x, y coordinates
            - h, w dimensions
        """
        try:
            page_source = info.page_source
        except:
            # Driver is no longer available - no page source to use
            return ''

        if 'xml' in page_source:
            root = html.fromstring(page_source.encode("utf-16"))
        else:
            root = html.fromstring(page_source)

        tree = root.getroottree()

        # Get elements' by xpath from given page source and
        all_elements_from_root = root.xpath('//*')
        all_elements_from_driver = info.find_elements_by_xpath("//*")

        if 'xml' in page_source:
            for index, el in enumerate(all_elements_from_root[2::]):
                # We bypass the first two elements of the list (/html and /html/body) - they have no map in the driver
                self._enrich_element(el, all_elements_from_driver[index].rect)
            return etree.tostring(root).decode("utf-8")

        for element in all_elements_from_root:
            element_xpath = tree.getpath(element)
            xpath_to_find = "./"
            if 'head' in element_xpath:
                xpath_to_find = f"./{element_xpath.split('/html/head')[1]}"

            if 'body' in element_xpath:
                xpath_to_find = f"./{element_xpath.split('/html/body')[1]}"

            if xpath_to_find != "./":
                driver_el = info.find_element_by_xpath(element_xpath)
                el = root.find(xpath_to_find)
                self._enrich_element(el, driver_el)

        # Return the enriched page source decoded from bytes
        return etree.tostring(root).decode("utf-8")

    def close(self) -> None:
        self.env.close()

    def _save_dataframe_to_csv(self, df: pd.DataFrame) -> None:
        if isfile(self._csv_file):  # it exists so append without writing the header
            df.to_csv(self._csv_file, index=False, mode='a', header=False)
        else:
            df.to_csv(self._csv_file, index=False)
