# Change analyzer

- [Change analyzer](#change-analyzer)
  - [Setup and usage in Windows environment](#setup-and-usage-in-windows-environment)
    - [1. Download required 3rd party softwares:](#1-download-required-3rd-party-softwares)
    - [2. Enable developer mode in Windows](#2-enable-developer-mode-in-windows)
    - [3. Create virtual environment](#3-create-virtual-environment)
    - [4. Create configuration file](#4-create-configuration-file)
    - [5. Run the software](#5-run-the-software)
    - [6. Compare results](#6-compare-results)
  - [Available commands](#available-commands)
  - [Configuration files](#configuration-files)

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
Example .ini file using WinAppDriver.exe and Windows platform:
```
  [driver]
  command_executor=http://127.0.0.1:4723
  platform=win
  app=/path/to/test/application.exe
```
Port of command_executor needs to match the driver's (ex. WinAppDriver/chromedriver) port.

[contributing]: CONTRIBUTING.md
