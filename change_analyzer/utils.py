from typing import Tuple, Dict

from PIL import Image, ImageOps
from shapely.geometry import Polygon


def image_pad_resize_to(im: Image, new_dims: Tuple[int, int]) -> Image:
    curr_dims = im.size

    new_ratio = new_dims[0] / new_dims[1]
    curr_ratio = curr_dims[0] / curr_dims[1]

    new_w = curr_dims[1] * new_ratio
    delta_w = new_w - curr_dims[0] if new_ratio > curr_ratio else 0

    new_h = curr_dims[0] / new_ratio
    delta_h = new_h - curr_dims[1] if new_ratio < curr_ratio else 0

    padding = (round(delta_w / 2), round(delta_h / 2))
    return ImageOps.expand(im, padding, "black").resize(new_dims, Image.ANTIALIAS)


def iou(rect0: Dict[str, int], rect1: Dict[str, int]) -> float:
    # self._logger.info(f"checking rects: {el0.rect}, {el1.rect}")
    # https://stackoverflow.com/a/42874377 or more compact: https://stackoverflow.com/a/57247833
    poly0 = Polygon([
        [rect0["x"], rect0["y"]],
        [rect0["x"] + rect0["width"], rect0["y"]],
        [rect0["x"] + rect0["width"], rect0["y"] + rect0["height"]],
        [rect0["x"], rect0["y"] + rect0["height"]]
    ])
    poly1 = Polygon([
        [rect1["x"], rect1["y"]],
        [rect1["x"] + rect1["width"], rect1["y"]],
        [rect1["x"] + rect1["width"], rect1["y"] + rect1["height"]],
        [rect1["x"], rect1["y"] + rect1["height"]]
    ])
    return poly0.intersection(poly1).area / poly0.union(poly1).area
