from selenium.webdriver.remote.webelement import WebElement

from change_analyzer.spaces.actions.app_action import AppAction


class ClickAppAction(AppAction):
    def __init__(self, el: WebElement) -> None:
        super(ClickAppAction, self).__init__(el)

    def perform(self) -> None:
        self.el.click()

    def __str__(self) -> str:
        if self.el.text:
            return f"click on {self.el.text}"
        elif self.el.get_attribute("HelpText"):
            return f"click on {self.el.get_attribute('HelpText')}"
        elif self.el.tag_name:
            return f"click on {self.el.tag_name}"
        else:
            return f"click on element from location ({self.el.location})"
