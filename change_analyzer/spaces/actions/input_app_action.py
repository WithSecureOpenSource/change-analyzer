from selenium.webdriver.remote.webelement import WebElement

from change_analyzer.spaces.actions.app_action import AppAction


class InputAppAction(AppAction):
    def __init__(self, el: WebElement, value: str) -> None:
        super(InputAppAction, self).__init__(el)
        self.value = value

    def perform(self) -> None:
        self.el.clear()
        self.el.send_keys(self.value)

    def __str__(self) -> str:
        return f"fill input {self.el.get_attribute('name')} with {self.value}"
