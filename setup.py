"""
Setup harness
"""
from setuptools import setup, find_packages
from distutils.util import convert_path


def _read_long_description():
    with open("README.md") as readme:
        return readme.read()


REQUIRE = [
    "gym==0.19.0",
    "appium-python-client==1.0.2",
    "Pillow",
    "pywinauto",
    "selenium",
    "faker",
    "jinja2",
    "pandas",
    "numpy",
    "matplotlib",
    "xmldiff",
    "beautifulsoup4",
    "lxml",
    "ludwig==0.5.5",
    "torch==1.11.0",
    "torchaudio==0.11.0",
    "torchinfo==1.7.0",
    "torchmetrics==0.8.2",
    "torchtext==0.12.0",
    "torchvision==0.12.0",
    "petastorm==0.11.3",
    "ludwig[viz]",
    "ludwig[image]"
]
DEV_REQUIRE = [
    "black",
    "jupyterlab",
    "pytest==6.2.5",
    "python-semantic-release",
    "twine",
    "wheel",
    "xenon",
]
NAME = "change-analyzer"
NAME_DASHED = NAME.replace("_", "-")

FILE_NAME = convert_path('change_analyzer/__init__.py')
with open(FILE_NAME) as FILE:
    for LINE in FILE:
        if "__version__" in LINE:
            VERSION_NUMBER = LINE[LINE.find('"')+1:LINE.rfind('"')]

setup(
    name=NAME_DASHED,
    description="Change analyzer",
    long_description=_read_long_description(),
    long_description_content_type="text/markdown",
    author="Matvey Pashkovskiy, Sorin Patrasoiu, Joona Oikarinen",
    author_email="",
    url=f"https://github.com/F-Secure/{NAME}",
    platforms="any",
    version=VERSION_NUMBER,
    packages=find_packages(exclude=[f"{NAME_DASHED}.tests", f"{NAME_DASHED}.tests.*"]),
    entry_points={
        "console_scripts": [
            "ca-run=change_analyzer.main:main",
            "ca-compare=change_analyzer.sequences_diff:main"
        ]
    },
    install_requires=REQUIRE,
    extras_require={"dev": DEV_REQUIRE},
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
)
