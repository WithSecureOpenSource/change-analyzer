from selenium.webdriver.remote.webelement import WebElement

from change_analyzer.spaces.actions.app_action import AppAction


class FormAppAction(AppAction):
    def __init__(self, form: WebElement) -> None:
        super(FormAppAction, self).__init__(form)

    def perform(self) -> None:
        # TODO basing on el
        #  * generate input values for fields
        #  * handle checkboxes, dropdowns, radios somehow
        #  * perform submit action (click input[type=submit]? what about standalone apps?)
        pass
