from selenium.webdriver.remote.webelement import WebElement


class AppAction:
    def __init__(self, el: WebElement) -> None:
        # TODO replace el with image. GUI testing is an visual task! can do `el.screenshot()` here
        self.el = el

    def perform(self) -> None:
        pass

    # def _get_xpath(self, el, current: str = "") -> Union[str, None]:
    #     el_tag = el.tag_name
    #     try:
    #         parent = el.find_element_by_xpath("..")
    #     except:
    #         return f"/{el_tag}[1]{current}"
    #
    #     count = 0
    #     children = parent.find_elements_by_xpath("*")
    #     for child in children:
    #         if el_tag == child.tag_name:
    #             count = count + 1
    #         if el.id == child.id:
    #             return self._get_xpath(parent, f"/{el_tag}[{count}]{current}")
    #     return None
