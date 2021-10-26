import logging
import random

from gym import Space
from selenium.webdriver.remote.webdriver import WebDriver

from change_analyzer.spaces.actions.app_action import AppAction
from change_analyzer.spaces.actions.click_app_action import ClickAppAction


class AllElementsAppActionSpace(Space):
    def __init__(self, driver: WebDriver) -> None:
        super(AllElementsAppActionSpace, self).__init__((), AppAction)
        self._logger = logging.getLogger(__name__)
        self.actions = set()
        self.driver = driver
        self.actions = {
            ClickAppAction(el) for el in self.driver.find_elements_by_xpath(f"//*")
        }
        self._logger.info(f"Found {len(self.actions)} actions on the screen")

    def sample(self) -> AppAction:
        return random.choice(list(self.actions))

    def contains(self, x: str) -> bool:
        # TODO implement __eq__() in AppAction
        return x in self.actions

    def __repr__(self) -> str:
        return f"AllElementsAppActionSpace({self.actions})"

    def __eq__(self, other: Space) -> bool:
        # TODO implement __eq__() in AppAction
        return (
            isinstance(other, AllElementsAppActionSpace)
            and self.actions == other.actions
        )
