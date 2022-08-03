import itertools
import logging
import random
from typing import List

from faker import Faker
from gym import Space
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from change_analyzer.spaces.actions.app_action import AppAction
from change_analyzer.spaces.actions.click_app_action import ClickAppAction


class DiscreteAppActionSpace(Space):
    ACTIONABLE_SELECTORS = {
        "web": {
            "buttons": {"button", "a", "select", "option", "input"},
            "inputs": {"input", "textarea"},
        },
        "win": {"buttons": {"Button", "MenuItem"}, "inputs": set()},
        "mobile": {"buttons": set(), "inputs": set()},
    }
    OVERLAPING_PERCENTAGE = 0.7
    SEED = 123
    NUMBER_OF_TEXT_SAMPLES = 3
    LOCALES = {"en_US", "fi_FI", "ja_JP"}

    def __init__(
        self,
        driver: WebDriver,
    ) -> None:
        super(DiscreteAppActionSpace, self).__init__((), AppAction)
        self._logger = logging.getLogger(__name__)
        self._fake = Faker(self.LOCALES)
        self._fake.seed_instance(self.SEED)
        self.actions = set()
        self.driver = driver
        self.actionable_selectors = set()
        self.update_actionable_selectors()
        self.actionable_elements = set()
        self.update_actionable_elements()
        self.update_current_actions()

    def update_actionable_selectors(self):
        self.actionable_selectors = self.ACTIONABLE_SELECTORS["win"]
        try:
            if self.driver.find_element_by_xpath("/*").tag_name == "html":
                self.actionable_selectors = self.ACTIONABLE_SELECTORS["web"]
        except Exception as e:
            self._logger.info(
                "Actionable selectors couldn't be updated due to an exception"
            )
            self._logger.info(e)

    def update_actionable_elements(self):
        try:
            self.actionable_elements = {
                el
                for selector in set.union(*self.actionable_selectors.values())
                for el in self.driver.find_elements_by_xpath(f"//*/{selector}")
                if self._is_el_clickable(el)
            }
            for el0, el1 in itertools.combinations(self.actionable_elements, 2):
                if self._overlap_percentage(el0, el1) > self.OVERLAPING_PERCENTAGE:
                    self.actionable_elements.remove(el1)
                if self._overlap_percentage(el1, el0) > self.OVERLAPING_PERCENTAGE:
                    self.actionable_elements.remove(el0)
        except Exception as e:
            self._logger.info(
                "Actionable elements couldn't be updated due to an exception"
            )
            self._logger.info(e)

    def update_current_actions(self):
        for el in self.actionable_elements:
            # if el.tag_name in actionable_selectors["buttons"]:
            self.actions.add(ClickAppAction(el))
            # if el.tag_name in actionable_selectors["inputs"]:
            #     # TODO how do we handle checkboxes, dropdowns, radios somehow?
            #     self.actions.update(
            #         {InputAppAction(el, value) for value in self._generate_values(el)}
            #     )
        self._logger.info(f"Found {len(self.actions)} actions on the screen")

    def get_action_based_on_string(self, action_string: str) -> AppAction:
        """
        Get action based on it's associated string
        :param action_string: the string of the action (element to use)
        :return: the actual AppAction
        """
        for action in list(self.actions):
            if action_string in str(action):
                return action

    def sample(self) -> AppAction:
        # return self.get_action_based_on_string('Manual scanning')
        return random.choice(list(self.actions))

    def contains(self, x: str) -> bool:
        # TODO implement __eq__() in AppAction
        return x in self.actions

    def __repr__(self) -> str:
        return f"DiscreteAppAction({self.actions})"

    def __eq__(self, other: Space) -> bool:
        # TODO implement __eq__() in AppAction
        return (
            isinstance(other, DiscreteAppActionSpace) and self.actions == other.actions
        )

    def _overlap_percentage(self, el0, el1) -> float:
        # TODO check that the elements are not overlaping
        # self._logger.info(f"checking rects: {el0.rect}, {el1.rect}")
        # https://stackoverflow.com/a/42874377 or more compact: https://stackoverflow.com/a/57247833
        return 0

    def _is_el_clickable(self, el: WebElement) -> bool:
        try:
            return (
                (el.rect["width"] != 0 or el.rect["height"] != 0)
                and el.is_enabled()
                and el.is_displayed()
            )
        except Exception as e:
            self._logger.info(
                f"Checking if element is clickable failed due to an exception due to an exception"
            )
            self._logger.info(e)
            return False

    def _generate_values(self, el: WebElement) -> List[str]:
        # TODO generate at least one valid value basing on input.get_attribute("name/type/min/max") and several invalid
        providers = {"address", "company", "email", "name", "phone_number", "ssn"}
        return [
            getattr(self._fake, provider)()
            for provider in providers
            for i in range(self.NUMBER_OF_TEXT_SAMPLES * len(self.LOCALES))
        ]
