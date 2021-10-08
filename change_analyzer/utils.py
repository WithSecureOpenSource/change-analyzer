from typing import Tuple

from PIL import Image, ImageOps


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
