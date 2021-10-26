from io import BytesIO
from typing import List

import pandas as pd
from PIL import Image
from selenium.webdriver.remote.webelement import WebElement


class AppAction:
    DEFAULT_FEATURES = ['rect.x', 'rect.y', 'rect.width', 'rect.height', 'tag_name', 'screenshot_as_png']

    def __init__(self, el: WebElement, features_to_extract: List[str] = DEFAULT_FEATURES) -> None:
        # TODO replace el with image. GUI testing is an visual task! can do `el.screenshot()` here
        self.el = el
        self.df = pd.DataFrame(
            [self._get_attr(el, attr) for attr in features_to_extract],
            columns=features_to_extract,
        )

    def perform(self) -> None:
        pass

    def _get_attr(self, object, attr):
        if attr == 'screenshot_as_png':
            stream = BytesIO(png)
            pic = Image.open(stream).convert("RGB")
            stream.close()
            return np.array(pic.getdata(), np.uint8).reshape(pic.size[1], pic.size[0], 3)

        path = attr.split(".")
        ref = object
        while path:
            element, path = path[0], path[1:]
            try:
                ref = getattr(ref, element)
            except:
                ref = ref[element]
        return ref

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
