from io import BytesIO
import time
from typing import Callable, Tuple, Dict, Union

import numpy as np
from PIL import Image, ImageGrab
from pywinauto import Desktop, Application
from selenium.webdriver.remote.webdriver import WebDriver

from change_analyzer.envs.web_driver_env import WebDriverEnv
from change_analyzer.spaces.actions.app_action import AppAction


class AppEnv(WebDriverEnv):
    def __init__(self, reset_app: Callable[[], WebDriver]) -> None:
        super(AppEnv, self).__init__(reset_app)
        self._initial_windows_without_sut = []

    def reset(self) -> Union[Dict, np.ndarray]:
        self._initial_windows_without_sut = self._get_current_open_windows()
        self._driver = self._reset_app()
        self._update_spaces()
        return self._observe()

    def step(self, action: AppAction) -> Tuple[Dict, float, bool, WebDriver]:
        # reward options:
        # - [CURRENT]reward if no exception was rised during the action
        # - len(self.action_space.actions - prev_action_space.actions) - we would like to find more new actions
        reward = 0
        try:
            self._logger.info(f"Perform action {str(action)}")
            action.perform()
            reward = 1
        except Exception as e:
            self._logger.error(e)
        finally:
            self._update_spaces()
            obs = self._observe()
            done = len(self.action_space.actions) == 0 or self._we_have_new_windows()
            info = self._driver
            return obs, reward, done, info

    def close(self) -> None:
        try:
            self._driver.close()
            self._driver.quit()
        except Exception as e:
            self._logger.info(
                "Due to an exception the driver couldn't be closed or quit"
            )
            self._logger.info(e)
        finally:
            # As one last thing to do when closing the env is to clean the opened windows
            time.sleep(2)
            current_open_windows = self._get_current_open_windows()

            for w in current_open_windows:
                if "F-Secure" in w or "Software updates" in w:
                    self._kill_app_based_on_window_title(window_title=w)

            # while not current_open_windows == initial_windows_without_sut:
            #     for w in current_open_windows:
            #         if w not in initial_windows_without_sut:
            #             self.kill_app_based_on_window_title(window_title=w)
            #     current_open_windows = self.get_current_open_windows()

    @staticmethod
    def _get_current_open_windows() -> list:
        """Get a list of all open windows"""

        windows = Desktop(backend="uia").windows()
        open_windows = [w.window_text() for w in windows]

        return open_windows

    def _kill_app_based_on_window_title(self, window_title: str):
        """Kill the app associated with the window title"""
        try:
            window = Desktop(backend="uia").windows(
                title=window_title, control_type="Window"
            )[0]
        except Exception as e:
            self._logger.info(
                f"Exception encountered when trying to find the window based on title {window_title}"
            )
            self._logger.error(e)
        # Get the window's handle
        try:
            window_handle = window.handle
            app = Application().connect(handle=window_handle)
            app.kill()
        except Exception as e:
            self._logger.info(
                f"Exception encountered when trying to kill the app based on title {window_title}"
            )
            self._logger.error(e)

    def _we_have_new_windows(self) -> bool:
        """Check if we have new windows, comparing the length of initial windows and current windows
        Initial windows do not contain the SUT window"""
        return (
                len(self._get_current_open_windows())
                > len(self._initial_windows_without_sut) + 1
        )

    def _get_screenshot(self) -> Image:
        try:
            stream = BytesIO(self._driver.get_screenshot_as_png())
            pic = Image.open(stream).convert("RGB")
            stream.close()
            return pic
        except Exception as e:
            self._logger.error(e)
            self._logger.info(f"Cannot get app screenshot. Taking full screen image")
            return ImageGrab.grab()
