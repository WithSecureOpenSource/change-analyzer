import argparse
import glob
import json
import os
import logging
from typing import Tuple, List

import numpy as np
import pandas as pd
import matplotlib.image as mpimg

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
        self.expected_images = None
        self.actual_images = None
        self.verdicts = []
        self.comments = []
        self.expected_steps = []
        self.actual_steps = []
        self.report_date = None
        self.df_merged = pd.DataFrame()

        self.sequence1_folder = sequence1_folder
        self.sequence2_folder = sequence2_folder
        self.update_sequence_files()
        self.update_report_file_path()
        self.update_sequences_date()
        self.create_comparisons_folder()
        self.step_count = 0

        self.validate_replay()

        self.write_to_report()

    def find_csv_file_within_folder(self, folder: str) -> str:

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
        sequence1_folder = os.path.dirname(self.sequence1_file)
        sequence2_folder = os.path.dirname(self.sequence2_file)
        self.sequence1_date = os.path.basename(sequence1_folder)
        self.sequence2_date = os.path.basename(sequence2_folder)

    def update_sequence_files(self):

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
        folder = os.path.join(os.path.dirname(self.sequence1_file), "comparisons")
        os.makedirs(folder, exist_ok=True)

    def update_report_file_path(self):
        """ The report file will always be within the first sequence folder"""
        self.expected_sequence_id = os.path.basename(self.sequence1_file).split('.')[0]
        self.actual_sequence_id = os.path.basename(self.sequence2_file).split('.')[0]
        self.report_date = datetime.now().strftime("%Y_%m_%d-%H_%M_%S")
        file_name = f'{self.expected_sequence_id}_vs_{self.actual_sequence_id}_{self.report_date}.html'
        self.report_file = os.path.join(os.path.dirname(self.sequence1_file), "comparisons", file_name)

    def validate_replay(self):
        df_sequence1 = pd.read_csv(self.sequence1_file)
        df_sequence2 = pd.read_csv(self.sequence2_file)
        self.df_merged = pd.merge(
            df_sequence1,
            df_sequence2,
            left_index=True,
            right_index=True,
            suffixes=('_expected', '_actual')
        )

        self.expected_steps = list(self.df_merged[f'{SequenceRecorder.COL_ACTION_TO_PERFORM}_expected'])
        self.actual_steps = list(self.df_merged[f'{SequenceRecorder.COL_ACTION_TO_PERFORM}_actual'])
        valid = self.validate_steps(self.expected_steps, self.actual_steps)

        if valid:
            self._logger.info("Actual steps are the same as expected steps")
            self.df_merged.apply(self.validate_steps_output, axis=1)
        else:
            self._logger.info("Actual steps are not the same as expected steps")

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

    @staticmethod
    def validate_actual_vs_expected_images(image_actual: str, image_expected: str) -> bool:
        """Validate actual image vs expected image of the same step"""
        # Convert images to arrays
        image_expected_as_array = np.array(json.loads(image_expected), dtype=np.uint8)
        image_actual_as_array = np.array(json.loads(image_actual), dtype=np.uint8)

        return np.array_equal(image_expected_as_array, image_actual_as_array)

    def save_step_images_from_arrays(self, image_actual: str, image_expected: str, filename_actual, filename_expected):

        folder = os.path.dirname(self.report_file)

        # Convert images to arrays
        image_expected_as_array = np.array(json.loads(image_expected), dtype=np.uint8)
        image_actual_as_array = np.array(json.loads(image_actual), dtype=np.uint8)

        expected_image_filepath = os.path.join(folder, filename_expected)
        actual_image_filepath = os.path.join(folder, filename_actual)

        mpimg.imsave(expected_image_filepath, image_expected_as_array)
        mpimg.imsave(actual_image_filepath, image_actual_as_array)

    def update_verdicts_and_comments(self, valid: bool):
        if valid:
            self.verdicts.append("pass")
            self.comments.append("The actual screenshot is the same as the expected screenshot")
        else:
            self.verdicts.append("fail")
            self.comments.append("The actual screenshot is not the same as the expected screenshot")

    def validate_steps_output(self, series: pd.Series):
        """Validate if each step's output is as expected"""

        image_expected = series[f'{SequenceRecorder.COL_ACTION_IMAGE_AFTER}_expected']
        image_actual = series[f'{SequenceRecorder.COL_ACTION_IMAGE_AFTER}_actual']

        # Validate actual vs expected images are the same
        valid = self.validate_actual_vs_expected_images(image_actual, image_expected)

        # Save images
        expected_image_filename = f"expected_screenshot_step{len(self.verdicts) + 2}_{self.report_date}.png"
        actual_image_filename = f"actual_screenshot_step{len(self.verdicts) + 2}_{self.report_date}.png"
        self.save_step_images_from_arrays(image_actual, image_expected, actual_image_filename, expected_image_filename)

        # Update verdicts and comments based on the step validation
        self.update_verdicts_and_comments(valid)

    def add_initial_step_to_sequences_data_components(self):
        """Add an initial step, Open Application, validate actual and expected images and save them"""

        # Add initial data regarding the first step
        self.expected_steps.insert(0, "open the Application")
        self.actual_steps.insert(0, "open the Application")
        self.expected_images.insert(0, f"expected_screenshot_step1_{self.report_date}")
        self.actual_images.insert(0, f"actual_screenshot_step1_{self.report_date}")

        # Get the images from merged DF
        expected_image = self.df_merged[f'{SequenceRecorder.COL_ACTION_IMAGE_BEFORE}_expected'][0]
        actual_image = self.df_merged[f'{SequenceRecorder.COL_ACTION_IMAGE_BEFORE}_actual'][0]

        # Save the step images
        expected_image_filename = f"expected_screenshot_step1_{self.report_date}.png"
        actual_image_filename = f"actual_screenshot_step1_{self.report_date}.png"
        self.save_step_images_from_arrays(actual_image, expected_image, actual_image_filename, expected_image_filename)

        # Validate step images
        valid = self.validate_actual_vs_expected_images(actual_image, expected_image)

        if valid:
            self.verdicts.insert(0, "pass")
            self.comments.insert(0, "The actual screenshot is the same as the expected screenshot")
        else:
            self.verdicts.insert(0, "fail")
            self.comments.insert(0, "The actual screenshot is not the same as the expected screenshot")

    def write_to_report(self):
        template_folder = os.path.abspath(os.path.join(__file__, "../templates"))
        file_loader = FileSystemLoader(template_folder)
        env = Environment(loader=file_loader, autoescape=True)
        template = env.get_template("Log_template.html")

        self.expected_images = [f'expected_screenshot_step{i+2}_{self.report_date}' for i in range(len(self.expected_steps))]
        self.actual_images = [f'actual_screenshot_step{i+2}_{self.report_date}' for i in range(len(self.actual_steps))]

        # Add the very first step
        self.add_initial_step_to_sequences_data_components()

        sequences_data = zip(self.expected_steps, self.actual_steps,
                             self.expected_images, self.actual_images,
                             self.verdicts, self.comments)

        steps = [f"step{i+1}" for i in range(len(self.expected_steps))]
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
