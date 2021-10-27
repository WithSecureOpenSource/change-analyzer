import base64
import logging
from io import BytesIO
from typing import Any, Callable, Tuple, Dict, Union

import gym
import numpy as np
from PIL import Image
from gym import spaces
from selenium.webdriver.remote.webdriver import WebDriver

from change_analyzer.spaces.actions.app_action import AppAction
from change_analyzer.spaces.discrete_app_action_space import DiscreteAppActionSpace
from change_analyzer.utils import image_pad_resize_to


class WebDriverEnv(gym.Env):
    metadata = {
        "render.modes": ["human", "base64", "rgb_array"],
        "video.frames_per_second": 1,
    }

    def __init__(self, reset_app: Callable[[], WebDriver]) -> None:
        super(WebDriverEnv, self).__init__()
        self._reset_app = reset_app
        self._driver = None
        self._logger = logging.getLogger(__name__)

    def reset(self) -> Union[Dict, np.ndarray]:
        self._driver = self._reset_app()
        self._update_spaces()
        return self._observe()

    def step(self, action: AppAction) -> Tuple[Dict, float, bool, WebDriver]:
        # reward options:
        # - [CURRENT]reward if no exception was rised during the action
        # - len(self.action_space.actions - prev_action_space.actions) - we would like to find more new actions
        reward = 0
        try:
            action.perform()
            reward = 1
        except Exception as e:
            self._logger.error(e)
        finally:
            self._update_spaces()
            obs = self._observe()
            done = len(self.action_space.actions) == 0
            info = self._driver
            return obs, reward, done, info

    def render(self, mode: str = "human") -> Union[Image.Image, str, np.ndarray]:
        pic = self._get_screenshot()

        if mode == "human":
            return pic

        if mode == "base64":
            buffer = BytesIO()
            pic.save(buffer, format="PNG")
            return base64.b64encode(buffer.getvalue()).decode("ascii")

        if mode == "rgb_array":
            dims = pic.size
            return np.array(pic.getdata(), np.uint8).reshape(dims[1], dims[0], 3)

        raise NotImplementedError(f"Mode {mode} is not supported by {__name__}")

    def close(self) -> None:
        try:
            self._driver.close()
            self._driver.quit()
        except:
            pass

    def _observe(self) -> Dict[str, Any]:
        return {"screenshot": self.render(), "has_error": 0}

    def _update_spaces(self) -> None:
        app_window_size = self._driver.get_window_size()
        # do we consider:
        # - window resizes
        # - new windows openings with different size
        self.observation_space = spaces.Dict(
            {
                "screenshot": spaces.Box(
                    low=0,  # brightness level low
                    high=255,  # brightness level high
                    shape=(app_window_size["height"], app_window_size["width"], 3),
                    dtype=np.uint8,
                ),
                "has_error": spaces.Discrete(2),
            }
        )
        self.action_space = DiscreteAppActionSpace(self._driver)

    def _get_screenshot(self) -> Image:
        # to take the entire screenshot https://stackoverflow.com/a/53825388 could be used
        body_el = self._driver.find_element_by_tag_name('body')
        self._driver.set_window_size(body_el.size['height'], body_el.size['width'])

        stream = BytesIO(self._driver.get_screenshot_as_png())
        pic = Image.open(stream).convert("RGB")
        stream.close()
        return pic
