import argparse
import glob
import json
import os
import logging
import re
import numpy as np
import pandas as pd
import xml.etree.ElementTree as ET

from os.path import basename, dirname
from typing import Tuple, List, Dict, Union
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw
from xmldiff import main as diffmain
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from change_analyzer.wrappers.sequence_recorder import SequenceRecorder


class SequencesDiff:

    SUPPORTED_DIFFS = ['UpdateAttrib']

    def __init__(self, sequence1_file: str, sequence2_file: str) -> None:
        self._logger = logging.getLogger(__name__)
        self.report_date = datetime.now().strftime("%Y_%m_%d-%H_%M_%S")
        self.sequence1_date = basename(dirname(sequence1_file))
        self.sequence2_date = basename(dirname(sequence2_file))
        self.expected_sequence_id = basename(sequence1_file).split('.')[0]
        self.actual_sequence_id = basename(sequence2_file).split('.')[0]
        self.report_folder = os.path.join(dirname(sequence1_file), "comparisons", self.report_date)
        os.makedirs(self.report_folder, exist_ok=True)
        self.df_merged = pd.DataFrame()

        self._update_merged_df(sequence1_file, sequence2_file)
        self._write_to_report(os.path.join(self.report_folder, 'index.html'))

    def _update_merged_df(self, sequence1_file, sequence2_file) -> None:
        """Update merged dataframe using expected and actual dataframes"""
        self.df_merged = pd.merge(
            pd.read_csv(sequence1_file),
            pd.read_csv(sequence2_file),
            left_index=True,
            right_index=True,
            suffixes=('_expected', '_actual')
        )

        # Add the first step into DF, based on current first row of DF
        first_step_action = 'open the Application'
        if 'html' in self.df_merged[f'{SequenceRecorder.COL_PAGE_SOURCE_BEFORE}_actual'][0]:
            first_step_action = 'open the Website URL'
        first_step_data = {
            f'{SequenceRecorder.COL_SEQUENCE_ID}_expected': self.df_merged[f'{SequenceRecorder.COL_SEQUENCE_ID}_expected'][0],
            f'{SequenceRecorder.COL_SEQUENCE_ID}_actual': self.df_merged[f'{SequenceRecorder.COL_SEQUENCE_ID}_actual'][0],
            f'{SequenceRecorder.COL_PAGE_SOURCE_AFTER}_actual': self.df_merged[f'{SequenceRecorder.COL_PAGE_SOURCE_BEFORE}_actual'][0],
            f'{SequenceRecorder.COL_PAGE_SOURCE_AFTER}_expected': self.df_merged[f'{SequenceRecorder.COL_PAGE_SOURCE_BEFORE}_expected'][0],
            f'{SequenceRecorder.COL_ACTION_IMAGE_AFTER}_actual': self.df_merged[f'{SequenceRecorder.COL_ACTION_IMAGE_BEFORE}_actual'][0],
            f'{SequenceRecorder.COL_ACTION_IMAGE_AFTER}_expected': self.df_merged[f'{SequenceRecorder.COL_ACTION_IMAGE_BEFORE}_expected'][0],
            f'{SequenceRecorder.COL_ACTION_TO_PERFORM}_expected': first_step_action,
            f'{SequenceRecorder.COL_ACTION_TO_PERFORM}_actual': first_step_action,
        }
        first_step_df = pd.DataFrame([first_step_data])
        self.df_merged = pd.concat([first_step_df, self.df_merged], ignore_index=True)
        compress_options = dict(method="zip", archive_name="df.csv")
        self.df_merged.to_csv(os.path.join(self.report_folder, 'df.csv.zip'), index=False, compression=compress_options)

        # Add Platform
        self.df_merged['Platform'] = np.where(self.df_merged['PageSourceAfter_actual'].str.contains('html') |
                                              self.df_merged['PageSourceBefore_actual'].str.contains('html'),
                                              'web', 'win')

        # Images
        img_col = [col for col in self.df_merged.columns if "image" in col.lower()]
        for col in img_col:
            self.df_merged.fillna({col: f"{np.zeros((1,1,3))}"}, inplace=True)
            self.df_merged[col] = self.df_merged[col].apply(self.json_to_image)
        self.df_merged["ImageVerdict"] = self.df_merged.apply(lambda row: "pass" if np.array_equal(
            row[f'{SequenceRecorder.COL_ACTION_IMAGE_AFTER}_expected'],
            row[f'{SequenceRecorder.COL_ACTION_IMAGE_AFTER}_actual']
        ) else "fail", axis=1)

        # XMLs
        xml_cols = [col for col in self.df_merged.columns if "pagesource" in col.lower()]
        for col in xml_cols:
            self.df_merged.fillna({col: '<?xml version="1.0" encoding="UTF-8"?><metadata></metadata>'}, inplace=True)
            self.df_merged[col] = self.df_merged[col].apply(self.encode_xml)

        self.df_merged["PageSource_diff"] = self.df_merged.apply(lambda row: self._extract_diffs_as_dict(
            row[f'{SequenceRecorder.COL_PAGE_SOURCE_AFTER}_expected'],
            row[f'{SequenceRecorder.COL_PAGE_SOURCE_AFTER}_actual'],
            row['Platform']
        ), axis=1)
        self.df_merged["DiffInfo"] = self.df_merged["PageSource_diff"].apply(self._get_diff_info)

        # Image highlighting
        self.df_merged.apply(lambda row: self._draw_boundaries(
            row["DiffInfo"],
            row[f'{SequenceRecorder.COL_ACTION_IMAGE_AFTER}_actual'],
            row[f'{SequenceRecorder.COL_ACTION_IMAGE_AFTER}_expected'],
        ), axis=1)
        self.df_merged["actual_screenshot_filename"] = self.df_merged.apply(lambda row: f"actual_screenshot_step{row.name + 1}.png", axis=1)
        self.df_merged["expected_screenshot_filename"] = self.df_merged.apply(lambda row: f"expected_screenshot_step{row.name + 1}.png", axis=1)

        self.df_merged.apply(lambda row: self._save_step_images(
            row[f'{SequenceRecorder.COL_ACTION_IMAGE_AFTER}_actual'],
            row[f'{SequenceRecorder.COL_ACTION_IMAGE_AFTER}_expected'],
            row["actual_screenshot_filename"],
            row["expected_screenshot_filename"],
        ), axis=1)

    @staticmethod
    def json_to_image(img: str) -> Union[Image.Image, float]:
        try:
            return Image.fromarray(np.array(json.loads(img), dtype=np.uint8))
        except:
            return np.nan

    @staticmethod
    def encode_xml(xml: str) -> Union[bytes, float]:
        encodings = re.findall(r'encoding=\"(.+?)\"', xml)
        if len(encodings) == 0:
            return xml.encode("utf-8")
        return xml.encode(encodings[0])

    def _save_step_images(self, image_actual: Image.Image, image_expected: Image.Image, filename_actual: str, filename_expected: str) -> None:
        """Save step expected and actual images of the SUT"""
        expected_image_filepath = os.path.join(self.report_folder, filename_expected)
        actual_image_filepath = os.path.join(self.report_folder, filename_actual)

        image_expected.save(expected_image_filepath, format="PNG")
        image_actual.save(actual_image_filepath, format="PNG")

    @staticmethod
    def _draw_boundaries(info_list: List[Dict], image_actual_pil: Image.Image, image_expected_pil: Image.Image) -> None:
        if len(info_list) == 0:
            return

        diff_type = {
            'UpdateAttrib': 'orange',
            'DeleteAttrib': 'red',
            'InsertAttrib': 'green'
        }
        for info in info_list:
            actual_element_boundaries = info['actual_element_boundaries']
            expected_element_boundaries = info['expected_element_boundaries']

            # Get outline color, based on diff type
            outline_color = diff_type[info['actual_element']['type']]

            # Draw boundaries
            draw_image_actual = ImageDraw.Draw(image_actual_pil)
            draw_image_expected = ImageDraw.Draw(image_expected_pil)
            draw_image_actual.polygon(actual_element_boundaries, fill=None, outline=outline_color)
            draw_image_expected.polygon(expected_element_boundaries, fill=None, outline=outline_color)

    def _write_to_report(self, report_file) -> None:
        """Write the report file using Jinja template"""
        template_folder = os.path.abspath(os.path.join(__file__, "../templates"))
        template = Environment(loader=FileSystemLoader(template_folder), autoescape=True).get_template("Log_template.html")

        self.expected_images = self.df_merged["expected_screenshot_filename"]
        self.actual_images = self.df_merged["actual_screenshot_filename"]
        verdicts = self.df_merged["ImageVerdict"].tolist()
        comments = ["The actual screenshot is the same as the expected screenshot"
                    if verdict == "pass"
                    else "The actual screenshot is not the same as the expected screenshot"
                    for verdict in verdicts]
        expected_steps = self.df_merged[f'{SequenceRecorder.COL_ACTION_TO_PERFORM}_expected'].tolist()
        actual_steps = self.df_merged[f'{SequenceRecorder.COL_ACTION_TO_PERFORM}_actual'].tolist()

        sequences_data = zip(expected_steps, actual_steps,
                             self.expected_images, self.actual_images,
                             verdicts, comments)

        steps = [f"step{i+1}" for i in range(len(expected_steps))]
        aria_controls = ",".join(steps)

        # Render HTML Template String
        html_template_string = template.render(expected_sequence_id=self.expected_sequence_id,
                                               actual_sequence_id=self.actual_sequence_id,
                                               sequences_data=sequences_data,
                                               report_date=self.report_date,
                                               aria_controls=aria_controls,
                                               sequence1_date=self.sequence1_date,
                                               sequence2_date=self.sequence2_date)

        # Save the new HTML file
        with open(report_file, "w") as f:
            f.write(html_template_string)

    @staticmethod
    def _diff_is_valid(diff: str) -> bool:
        """Check if diff doesn't contain ignored diffs
        Currently we don't check a diff further if it contains the following strings:
            - ProcessId
            - RuntimeId
            - script
        """
        ignored_diffs = ['ProcessId', 'RuntimeId', 'script']
        return not any(ignored_diff.lower() in diff.lower() for ignored_diff in ignored_diffs)

    @staticmethod
    def _get_attribute_value_based_on_node(page_root: ET.Element, node: str, attribute: str) -> str:
        """Get attribute value for specific node from given page source"""
        formatted_node = "./" + "/".join(node.split("/")[2::])
        elem = page_root.findall(formatted_node)[0]
        return elem.attrib[attribute]

    def _extract_diffs_as_dict(self, expected_xml: str, actual_xml: str, platform: str) -> Dict:
        """Extract diffs as dictionary, using expected and actual approach"""
        diffs_as_dict = {
            'expected': {},
            'actual': {}
        }

        if platform == 'web':
            # We need to preprocess the html to be xml-like
            expected_xml = BeautifulSoup(expected_xml, 'html.parser').prettify()
            actual_xml = BeautifulSoup(actual_xml, 'html.parser').prettify()

        expected_root = ET.ElementTree(ET.fromstring(expected_xml)).getroot()
        actual_root = ET.ElementTree(ET.fromstring(actual_xml)).getroot()

        for diff in diffmain.diff_texts(expected_xml, actual_xml):
            diff_type = str(diff).split("(")[0]
            if self._diff_is_valid(str(diff)) and diff_type in self.SUPPORTED_DIFFS:
                expected_value = self._get_attribute_value_based_on_node(expected_root, diff.node, diff.name)
                if diff.node not in diffs_as_dict['actual'].keys():
                    diffs_as_dict['actual'][diff.node] = {diff.name: diff.value}
                    diffs_as_dict['actual'][diff.node] = {'type': diff_type}
                    diffs_as_dict['expected'][diff.node] = {diff.name: expected_value}
                else:
                    diffs_as_dict['actual'][diff.node][diff.name] = diff.value
                    diffs_as_dict['expected'][diff.node][diff.name] = expected_value

        # Update each node from dict with expected and actual x,y,w,h if they are not already present
        for k, v in diffs_as_dict['actual'].items():
            expected_element = diffs_as_dict['expected'][k]
            actual_element = diffs_as_dict['actual'][k]
            if 'x' not in diffs_as_dict['actual'][k].keys():
                expected_x = self._get_attribute_value_based_on_node(expected_root, k, 'x')
                actual_x = self._get_attribute_value_based_on_node(actual_root, k, 'x')
                expected_element['x'] = expected_x
                actual_element['x'] = actual_x
            if 'y' not in diffs_as_dict['actual'][k].keys():
                expected_y = self._get_attribute_value_based_on_node(expected_root, k, 'y')
                actual_y = self._get_attribute_value_based_on_node(actual_root, k, 'y')
                expected_element['y'] = expected_y
                actual_element['y'] = actual_y
            if 'width' not in diffs_as_dict['actual'][k].keys():
                expected_width = self._get_attribute_value_based_on_node(expected_root, k, 'width')
                actual_width = self._get_attribute_value_based_on_node(actual_root, k, 'width')
                expected_element['width'] = expected_width
                actual_element['width'] = actual_width
            if 'height' not in diffs_as_dict['actual'][k].keys():
                expected_height = self._get_attribute_value_based_on_node(expected_root, k, 'height')
                actual_height = self._get_attribute_value_based_on_node(actual_root, k, 'height')
                expected_element['height'] = expected_height
                actual_element['height'] = actual_height

        return diffs_as_dict

    def _get_diff_info(self, diff_results: Dict) -> List[Dict]:
        if diff_results['expected'] == {} or diff_results['actual'] == {}:
            return []

        step_diff_info = []
        for element in diff_results['actual'].keys():
            expected_element = diff_results['expected'][element]
            actual_element = diff_results['actual'][element]

            expected_x = expected_element['x']
            actual_x = actual_element['x']
            expected_y = expected_element['y']
            actual_y = actual_element['y']
            expected_width = expected_element['width']
            actual_width = actual_element['width']
            expected_height = expected_element['height']
            actual_height = actual_element['height']

            expected_box_coordinates = self._get_box_coordinates(expected_x, expected_y,
                                                                 expected_width, expected_height)
            actual_box_coordinates = self._get_box_coordinates(actual_x, actual_y,
                                                               actual_width, actual_height)
            info = f'Actual ({actual_box_coordinates}) vs expected ({expected_box_coordinates})'

            step_diff_info.append({
                'actual_element': actual_element,
                'expected_element': expected_element,
                'actual_element_boundaries': actual_box_coordinates,
                'expected_element_boundaries': expected_box_coordinates,
                'info': info
            })

        return step_diff_info

    @staticmethod
    def _get_box_coordinates(x: str, y: str, w: str, h: str) -> List[Tuple[int, int]]:
        """Get boundary coordinates based on x, y, width and height"""
        x = int(x)
        y = int(y)
        w = int(w)
        h = int(h)
        return [(x, y), (x+w, y), (x+w, y+h), (x, y+h)]


def find_csv_file_within_folder(folder: str) -> str:
    """"Find the sequence csv file within the associated folder, assuming there is only one csv file present"""
    try:
        return glob.glob(os.path.join(os.getcwd(), "recordings", folder, "*.csv"))[0]
    except:
        pass

def find_last_two_valid_folders() -> Tuple[str, str]:
    """Find the last two folders which have a csv file"""
    folders_found = 0
    csv_file_paths = []
    recordings_folder = os.path.join(os.path.abspath(os.getcwd()), 'recordings')
    os.chdir(recordings_folder)
    folders = list(filter(os.path.isdir, os.listdir(recordings_folder)))
    folders = [os.path.join(recordings_folder, f) for f in folders]  # add path to each file
    folders.sort(key=lambda x: os.path.getmtime(x))
    folders.reverse()

    for folder in folders:
        csv_file_path = find_csv_file_within_folder(folder)
        if csv_file_path:
            folders_found += 1
            csv_file_paths.append(csv_file_path)
        if folders_found == 2:
            break

    return csv_file_paths[0], csv_file_paths[1]


def compare(sequence1_folder: str = "", sequence2_folder: str = ""):
    sequence1_file = ""
    sequence2_file = ""
    if not sequence1_folder and not sequence2_folder:
        sequence1_file, sequence2_file = find_last_two_valid_folders()

    if sequence1_folder and not sequence2_folder:
        sequence1_file = find_csv_file_within_folder(sequence1_folder)
        sequence2_file, _ = find_last_two_valid_folders()

    if sequence1_folder and sequence2_folder:
        sequence1_file = find_csv_file_within_folder(sequence1_folder)
        sequence2_file = find_csv_file_within_folder(sequence2_folder)

    SequencesDiff(sequence1_file, sequence2_file)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sequence1_folder",
        help="recordings folder with the expected sequence",
        required=False,
    )
    parser.add_argument(
        "--sequence2_folder",
        help="recordings folder with the expected sequence",
        required=False,
    )
    args = parser.parse_args()
    compare(args.sequence1_folder, args.sequence2_folder)


if __name__ == "__main__":
    main()
