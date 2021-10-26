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
from change_analyzer.spaces.all_elements_app_action_space import AllElementsAppActionSpace
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
        self._prev_screenshot = None

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
            reward = self._calc_reward()
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
        prev_dims = self._prev_screenshot.size
        curr_dims = pic.size
        if (prev_dims is not None) and (prev_dims != curr_dims):
            pic = image_pad_resize_to(pic, prev_dims)
        self._prev_screenshot = pic

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
        # self.action_space = DiscreteAppActionSpace(self._driver)
        self.action_space = AllElementsAppActionSpace(self._driver)

    def _get_screenshot(self) -> Image:
        # to take the entire screenshot https://stackoverflow.com/a/53825388 could be used
        stream = BytesIO(self._driver.get_screenshot_as_png())
        pic = Image.open(stream).convert("RGB")
        stream.close()
        return pic

    def _calc_reward(self) -> int:
        if self._prev_screenshot is None:
            raise Exception("Previous screenshot is not stored, call reset() before using the environment")

        dims = self._prev_screenshot.size
        diff = np.subtract(np.array(self._prev_screenshot.getdata(), np.uint8).reshape(dims[1], dims[0], 3), self.render("rgb_array")).flatten()
        # TODO discount could be added if the screen was seen before
        return np.nonzero(diff)[0].size

