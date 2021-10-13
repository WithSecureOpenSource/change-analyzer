import argparse
import glob
import json
import os
import logging
import re
from typing import Tuple, List, Dict, Union

import PIL.Image
import numpy as np
import pandas as pd
from PIL import Image
from PIL import ImageDraw

from xmldiff import main as diffmain
import xml.etree.ElementTree as ET
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from change_analyzer.wrappers.sequence_recorder import SequenceRecorder


class SequencesDiff:

    def __init__(self, sequence1_folder: str = None, sequence2_folder: str = None) -> None:
        # - If sequence1 and sequence2 folders are not provided, we test the last two sequences
        # - If only sequence1 folder is provided, we test it against the last valid sequence
        self._logger = logging.getLogger(__name__)

        self.sequence1_file = None
        self.sequence2_file = None
        self.sequence1_date = None
        self.sequence2_date = None
        self.report_file = None
        self.expected_sequence_id = None
        self.actual_sequence_id = None
        self.report_date = datetime.now().strftime("%Y_%m_%d-%H_%M_%S")
        self.df_merged = pd.DataFrame()

        self.sequence1_folder = sequence1_folder
        self.sequence2_folder = sequence2_folder
        self.update_sequence_files()
        self.update_report_file_path()
        self.update_sequences_date()
        self.create_comparisons_folder()

        self.update_merged_df()
        self._write_to_report()

    def find_csv_file_within_folder(self, folder: str) -> str:
        """"Find the sequence csv file within the associated folder, assuming there is only one csv file present"""
        try:
            csv_file = glob.glob(os.path.join(os.getcwd(), "recordings", folder, "*.csv"))[0]
            self._logger.info("csv file found ", csv_file)
            return csv_file
        except Exception as e:
            self._logger.info("We couldn't find any csv file within the folder due to an exception")
            self._logger.info(e)

    def find_last_two_valid_folders(self) -> Tuple[str, str]:
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
            csv_file_path = self.find_csv_file_within_folder(folder)
            if csv_file_path:
                folders_found += 1
                csv_file_paths.append(csv_file_path)
            if folders_found == 2:
                break

        return csv_file_paths[0], csv_file_paths[1]

    def update_sequences_date(self):
        """Update sequence date for both expected and actual sequence"""
        sequence1_folder = os.path.dirname(self.sequence1_file)
        sequence2_folder = os.path.dirname(self.sequence2_file)
        self.sequence1_date = os.path.basename(sequence1_folder)
        self.sequence2_date = os.path.basename(sequence2_folder)

    def update_sequence_files(self):
        """Update sequence files to point to their respective csv files"""
        if not self.sequence1_folder and not self.sequence2_folder:
            self.sequence1_file, self.sequence2_file = self.find_last_two_valid_folders()
            self._logger.info("We have no sequence defined.")

        if self.sequence1_folder and not self.sequence2_folder:
            self.sequence1_file = self.find_csv_file_within_folder(self.sequence1_folder)
            self.sequence2_file, _ = self.find_last_two_valid_folders()
            self._logger.info("We have only expected sequence defined.")

        if self.sequence1_folder and self.sequence2_folder:
            self.sequence1_file = self.find_csv_file_within_folder(self.sequence1_folder)
            self.sequence2_file = self.find_csv_file_within_folder(self.sequence2_folder)
            self._logger.info("We have both sequences defined.")

        self._logger.info("We use sequence1: ", self.sequence1_file)
        self._logger.info("We use sequence2: ", self.sequence2_file)

    def create_comparisons_folder(self):
        """Create comparisons folder within expected sequence if it doesn't already exist"""
        folder = os.path.join(os.path.dirname(self.sequence1_file), "comparisons", self.report_date)
        os.makedirs(folder, exist_ok=True)

    def update_report_file_path(self):
        """ The report file will always be within the first sequence folder"""
        self.expected_sequence_id = os.path.basename(self.sequence1_file).split('.')[0]
        self.actual_sequence_id = os.path.basename(self.sequence2_file).split('.')[0]
        self.report_file = os.path.join(os.path.dirname(self.sequence1_file), "comparisons", self.report_date, 'index.html')

    def update_merged_df(self):
        """Update merged dataframe using expected and actual dataframes"""
        self.df_merged = pd.merge(
            pd.read_csv(self.sequence1_file),
            pd.read_csv(self.sequence2_file),
            left_index=True,
            right_index=True,
            suffixes=('_expected', '_actual')
        )

        # Add the first step into DF, based on current first row of DF
        first_step_data = {
            f'{SequenceRecorder.COL_SEQUENCE_ID}_expected': self.df_merged[f'{SequenceRecorder.COL_SEQUENCE_ID}_expected'][0],
            f'{SequenceRecorder.COL_SEQUENCE_ID}_actual': self.df_merged[f'{SequenceRecorder.COL_SEQUENCE_ID}_actual'][0],
            f'{SequenceRecorder.COL_PAGE_SOURCE_AFTER}_actual': self.df_merged[f'{SequenceRecorder.COL_PAGE_SOURCE_BEFORE}_actual'][0],
            f'{SequenceRecorder.COL_PAGE_SOURCE_AFTER}_expected': self.df_merged[f'{SequenceRecorder.COL_PAGE_SOURCE_BEFORE}_expected'][0],
            f'{SequenceRecorder.COL_ACTION_IMAGE_AFTER}_actual': self.df_merged[f'{SequenceRecorder.COL_ACTION_IMAGE_BEFORE}_actual'][0],
            f'{SequenceRecorder.COL_ACTION_IMAGE_AFTER}_expected': self.df_merged[f'{SequenceRecorder.COL_ACTION_IMAGE_BEFORE}_expected'][0],
            f'{SequenceRecorder.COL_ACTION_TO_PERFORM}_expected': 'open the Application',
            f'{SequenceRecorder.COL_ACTION_TO_PERFORM}_actual': 'open the Application',
        }
        first_step_df = pd.DataFrame([first_step_data])
        self.df_merged = pd.concat([first_step_df, self.df_merged], ignore_index=True)
        self._save_dataframe_to_csv()

        self.df_merged["StepVerdict"] = self.df_merged.apply(lambda row: np.array_equal(
            row[f'{SequenceRecorder.COL_ACTION_TO_PERFORM}_expected'],
            row[f'{SequenceRecorder.COL_ACTION_TO_PERFORM}_actual']
        ), axis=1)
        # TODO log the result of self.df_merged["StepVerdict"].all()

        # Images
        img_col = [col for col in self.df_merged.columns if "image" in col.lower()]
        for col in img_col:
            self.df_merged[col] = self.df_merged[col].apply(self.json_to_image)
        self.df_merged["ImageVerdict"] = self.df_merged.apply(lambda row: "pass" if np.array_equal(
            row[f'{SequenceRecorder.COL_ACTION_IMAGE_AFTER}_expected'],
            row[f'{SequenceRecorder.COL_ACTION_IMAGE_AFTER}_actual']
        ) else "fail", axis=1)

        # XMLs
        xml_cols = [col for col in self.df_merged.columns if "pagesource" in col.lower()]
        for col in xml_cols:
            self.df_merged[col] = self.df_merged[col].apply(self.encode_xml)

        self.df_merged["PageSource_diff"] = self.df_merged.apply(lambda row: self.extract_diffs_as_dict(
            row[f'{SequenceRecorder.COL_PAGE_SOURCE_AFTER}_expected'],
            row[f'{SequenceRecorder.COL_PAGE_SOURCE_AFTER}_actual']
        ), axis=1)
        self.df_merged["DiffInfo"] = self.df_merged["PageSource_diff"].apply(self.get_diff_info)

        # Image highlighting
        self.df_merged.apply(lambda row: self.draw_boundaries(
            row["DiffInfo"],
            row[f'{SequenceRecorder.COL_ACTION_IMAGE_AFTER}_actual'],
            row[f'{SequenceRecorder.COL_ACTION_IMAGE_AFTER}_expected'],
        ), axis=1)
        self.df_merged["actual_screenshot_filename"] = self.df_merged.apply(lambda row: f"actual_screenshot_step{row.name + 1}_{self.report_date}.png", axis=1)
        self.df_merged["expected_screenshot_filename"] = self.df_merged.apply(lambda row: f"expected_screenshot_step{row.name + 1}_{self.report_date}.png", axis=1)

        self.df_merged.apply(lambda row: self.save_step_images(
            row[f'{SequenceRecorder.COL_ACTION_IMAGE_AFTER}_actual'],
            row[f'{SequenceRecorder.COL_ACTION_IMAGE_AFTER}_expected'],
            row["actual_screenshot_filename"],
            row["expected_screenshot_filename"],
        ), axis=1)

    @staticmethod
    def json_to_image(img: str) -> Union[PIL.Image.Image, float]:
        try:
            return Image.fromarray(np.array(json.loads(img), dtype=np.uint8))
        except:
            return np.nan

    @staticmethod
    def encode_xml(xml: str) -> Union[bytes, float]:
        try:
            return xml.encode(re.findall(r'encoding=\"(.+?)\"', xml)[0])
        except:
            return np.nan

    def validate_steps(self, expected_steps: List[str], actual_steps: List[str]) -> bool:
        """Validate if the performed steps are the same"""

        if len(expected_steps) != len(actual_steps):
            self._logger.info("The amount of actual steps is not the same as the amount of performed steps")
            self._logger.info(f"Actual steps: {len(actual_steps)}\n", actual_steps)
            self._logger.info(f"Expected steps: {len(expected_steps)}\n", expected_steps)
            return False

        if expected_steps == actual_steps:
            self._logger.info("Actual steps are the same as expected steps\n", actual_steps)
            return True

        self._logger.info("Actual steps are not the same as expected steps")
        for i, step in enumerate(expected_steps):
            expected_step = expected_steps[i]
            actual_step = actual_steps[i]
            if expected_step != actual_step:
                self._logger.info(f"Step {i+1} is not as expected. Expected {expected_step} and found {actual_step}")
                return False

        return True

    def save_step_images(self, image_actual: PIL.Image.Image, image_expected: PIL.Image.Image, fn_actual: str, fn_expected: str):
        """Save step expected and actual images of the SUT"""
        folder = os.path.dirname(self.report_file)

        expected_image_filepath = os.path.join(folder, fn_expected)
        actual_image_filepath = os.path.join(folder, fn_actual)

        image_expected.save(expected_image_filepath, format="PNG")
        image_actual.save(actual_image_filepath, format="PNG")

    @staticmethod
    def draw_boundaries(info_list: List[Dict], image_actual_pil: PIL.Image.Image, image_expected_pil: PIL.Image.Image):
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

    def _write_to_report(self):
        """Write the report file using Jinja template"""
        template_folder = os.path.abspath(os.path.join(__file__, "../templates"))
        file_loader = FileSystemLoader(template_folder)
        env = Environment(loader=file_loader, autoescape=True)
        template = env.get_template("Log_template.html")

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
        with open(self.report_file, "w") as f:
            f.write(html_template_string)

    @staticmethod
    def get_attribute_value_based_on_node(page_root: ET.Element, node: str, attribute: str) -> str:
        """Get attribute value for specific node from given page source"""
        formatted_node = "./" + "/".join(node.split("/")[2::])
        elem = page_root.findall(formatted_node)[0]
        return elem.attrib[attribute]

    def extract_diffs_as_dict(self, expected_xml: str, actual_xml: str) -> Dict:
        """Extract diffs as dictionary, using expected and actual approach"""

        diffs_list = diffmain.diff_texts(expected_xml, actual_xml)

        expected_tree = ET.ElementTree(ET.fromstring(expected_xml))
        expected_root = expected_tree.getroot()
        actual_tree = ET.ElementTree(ET.fromstring(actual_xml))
        actual_root = actual_tree.getroot()

        diffs_as_dict = {
            'expected': {},
            'actual': {}
        }

        for diff in diffs_list:
            if 'ProcessId' not in diff and 'RuntimeId' not in diff:
                diff_type = str(diff).split("(")[0]
                expected_value = self.get_attribute_value_based_on_node(expected_root, diff.node, diff.name)
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
                expected_x = self.get_attribute_value_based_on_node(expected_root, k, 'x')
                actual_x = self.get_attribute_value_based_on_node(actual_root, k, 'x')
                expected_element['x'] = expected_x
                actual_element['x'] = actual_x
            if 'y' not in diffs_as_dict['actual'][k].keys():
                expected_y = self.get_attribute_value_based_on_node(expected_root, k, 'y')
                actual_y = self.get_attribute_value_based_on_node(actual_root, k, 'y')
                expected_element['y'] = expected_y
                actual_element['y'] = actual_y
            if 'width' not in diffs_as_dict['actual'][k].keys():
                expected_width = self.get_attribute_value_based_on_node(expected_root, k, 'width')
                actual_width = self.get_attribute_value_based_on_node(actual_root, k, 'width')
                expected_element['width'] = expected_width
                actual_element['width'] = actual_width
            if 'height' not in diffs_as_dict['actual'][k].keys():
                expected_height = self.get_attribute_value_based_on_node(expected_root, k, 'height')
                actual_height = self.get_attribute_value_based_on_node(actual_root, k, 'height')
                expected_element['height'] = expected_height
                actual_element['height'] = actual_height

        return diffs_as_dict

    def get_diff_info(self, diff_results: Dict) -> List[Dict]:
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

    def _save_dataframe_to_csv(self) -> None:
        """Save merged dataframe to the csv"""
        csv_file = self.report_file.split(".")[0] + ".csv"
        self.df_merged.to_csv(csv_file, index=False)


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

    SequencesDiff(sequence1_folder=args.sequence1_folder, sequence2_folder=args.sequence2_folder)


if __name__ == "__main__":
    main()
