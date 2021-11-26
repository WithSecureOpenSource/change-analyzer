# Change analyzer

- [Change analyzer](#change-analyzer)
  - [About](#about)
    - [Main Data features](#main-data-features)
    - [Data Collection](#data-collection)
    - [Data Reconstruction](#data-reconstruction)
    - [Data Analysis](#data-analysis)
    - [Data Validation](#data-validation)
  - [Setup and usage in Windows environment](#setup-and-usage-in-windows-environment)
    - [1. Download required 3rd party softwares:](#1-download-required-3rd-party-softwares)
    - [2. Enable developer mode in Windows](#2-enable-developer-mode-in-windows)
    - [3. Create virtual environment](#3-create-virtual-environment)
    - [4. Create configuration file](#4-create-configuration-file)
    - [5. Run the software](#5-run-the-software)
    - [6. Compare results](#6-compare-results)
  - [Available commands](#available-commands)
  - [Configuration files](#configuration-files)
  - [Acknowledgement](#acknowledgement)

## About
Change-Analyzer (CA in short) is a framework built utilizing ML techniques, leveraging [OpenAI Gym library](https://gym.openai.com/). 
CA allows product teams to get feedback regarding their software product, aka SUT (System Under Test).

### Main Data features
Essentially, is built around the following main Data features:
* [Data Collection](#data-collection), done through Automated Exploratory Testing
* [Data Reconstruction](#data-reconstruction), done through Automated Regression Testing
* [Data Analysis](#data-analysis), done through Change Detection
* [Data Validation](#data-validation), done through Verdict Generation

### Data Collection
After installation and configuration (see sections below) Data Collection can be started.
An agent is exploring the SUT without prior knowledge of it, recording testing sequence and state of the application.
Once the execution is completed, the Data is saved in a csv file, available in a dedicated folder, from recordings.
Currently, the Data consists of the following information regarding the steps of the executed sequence:
* [Timestamp](#): an Integer with the execution time in epoch 	
* [SequenceId](#): a String with a unique ID to identify the sequence
* [PageSourceBefore](#): a String with the page source (before step execution)
* [PageSourceAfter](#): a String with the page source (after step execution)
* [ActionToPerform](#): a String with the action that will be performed next
* [ActionImageBefore](#): a numpy.ndarray with the image of SUT (before step execution)
* [ActionImageAfter](#): a numpy.ndarray with the image of SUT (after step execution)

### Data Reconstruction
Once several sequences exist, they can be used for Data Reconstruction.
An agent is rerunning the specified existing sequence, recording a new state of the application.
Data collected has the same structure as described in the above section.

### Data Analysis
In this phase, two sequences are analyzed. The sequences are the same, from steps perspective, but are executed against 
different SUT versions.</br>
A report is created, to showcase the differences between the two sequences, if any. The goal is to provide a visual tool 
for change detection.</br>
The report will contain the following info:
* The info regarding which is the expected sequence and which is the actual sequence
* A visual indicator for each step if it was considered passed or failed
* A description of the executed steps step
* A short info to support the step status
* Expected image of the SUT, from expected sequence
* Actual image of the SUT, from actual sequence
* Actual and expected images may contain highlighted elements, if they were detected to be part of a change

### Data Validation
Using ML techniques, in this phase, the tool should be able to say if the detected changes are expected behavior of faults in the SUT.
Data Validation will be cover in more details later, because currently is in planning phase.

## Setup and usage in Windows environment
### 1. Download required 3rd party softwares: 
* Download <a href="https://www.selenium.dev/downloads/">Selenium standalone server</a>.
  * Version 3.141.59 confirmed as working.
  * Put .jar file to place where you can easily find it.
* FOR DESKTOP APP TESTING: Download <a href="https://github.com/microsoft/WinAppDriver">Windows Application Driver</a>.
  * Version 1.2.1 confirmed as working.
  * Install downloaded .msi file.
* FOR WEBSITE TESTING: Download <a href="https://chromedriver.chromium.org/downloads">Chrome driver</a>.
  * Version 94.0.4606.61 confirmed as working.
  * Put binary file to place where you can easily find it.

### 2. Enable developer mode in Windows
* Windows logo -> developer settings -> Enable
  * <a href="https://docs.microsoft.com/en-us/windows/apps/get-started/enable-your-device-for-development#accessing-settings-for-developers">Official documentation</a> if needed.

### 3. Create virtual environment
#### 3.1. Virtualenv option 
Requires Python 3.7 or newer installed and added to PATH variable.

* Run ```install.bat``` located in source code root directory.
  * This script will install necessary dependencies defined in setup.py.

#### 3.2. Conda option
If preferred, it is also possible to use a Conda environment.

* Open an Anaconda terminal and go to project's main folder
* Run `conda env create -f requirements.yml`
* The above command will create the conda environment `change_analyzer` including all the needed dependencies
* In order to use the Conda environment, you can either attach it to a project within your favorite IDE, or activate
it on command line with `conda activate change_analyzer`

### 4. Create configuration file
It's mandatory to tell change-analyzer how to execute testing. For this reason .ini configuration is needed. Create configure now before running the software.
  * <a href="#configuration-files">More details</a> can be found in later part of this README.

### 5. Run the software
Requires Java 8 installed and added to PATH variable.

* Start Selenium standalone server:
  * Open CMD and change directory to Selenium directory (downloaded in step 1).
  * ```java -jar selenium-server-standalone-[version].jar```
    * Version needs to be change accordingly.
  * Minimize CMD and let it run on background.
* FOR DESKTOP APP TESTING: Start Windows Application Driver
  * Run ```WinAppDriver.exe```
    * Default location C:\Program Files (x86)\Windows Application Driver
  * Minimize CMD and let it run on background.
* FOR WEBSITE TESTING:
  * Run ```chromedriver.exe```
  * Minimize CMD and let it run on background.
* Run the software:
  * Open CMD and change directory to source code root.
  * Activate virtual environment: ```.venv\Scripts\activate```
  * Generate new report: ```ca-run --config [configuration filename].ini```
* Results appear in *recordings* directory.

### 6. Compare results
Requires two generated test results.

* Open CMD and change directory to source code root.
* Activate virtual environment: ```.venv\Scripts\activate```
* Compare results: ```ca-compare --sequence1_folder [Test folder 1] --sequence2_folder [Test folder 2]```
  * Replace [Test folder 1] with real results folder name (example 2021_10_05-14_15_00).
  * Test results are generated to *recordings* directory.
  * Argument paths starts from *recordings* directory.

## Available commands
* ```ca-run```
  * Used to generate new test results.
  * Requires ```--config``` parameter. Defines which .ini file to use.
  * Replay mode available using ```--csv_folder``` parameter.
  * Results can be found under *recordings* directory.
* ```ca-compare```
  * Used to compare two test results.
  * Define test directories with ```--sequence1_folder``` and ```--sequence2_folder``` parameters.
  * Results can be found under sequence 1 directory.

## Configuration files
This project uses <a href="https://docs.python.org/3/library/configparser.html">.ini files</a> as configure files to change software's behavior. **User must define own configuration files.** Ini file must define following values:
```
  [driver]
  command_executor=
  platform=
  app=
```
Example .ini file using WinAppDriver and Windows platform:
```
  [driver]
  command_executor=http://127.0.0.1:4723
  platform=win
  app=/path/to/test/application.exe
```
Example .ini file using SeleniumDriver and Web platform:
```
  [driver]
  command_executor=http://127.0.0.1:4444/wd/hub
  platform=web
  url=https://learn.ivves.eu/
```
Port of command_executor needs to match the driver's (ex. WinAppDriver/chromedriver) port.

## Acknowledgement
The package was developed by [F-Secure Corporation][f-secure] in scope of [IVVES project][ivves]. This work was labelled by [ITEA3][itea3] and funded by local authorities under grant agreement 'ITEA-2019-18022-IVVES'.

[contributing]: CONTRIBUTING.md
[ivves]: http://ivves.eu/
[itea3]: https://itea3.org/
[f-secure]: https://www.f-secure.com/en
