# Spatineo-GIS-project
GIS software development project for Spatineo Oy done as a part of the Project Course at Aalto University


## Requirements and installation
This program runs on Python 3. Python can installed e.g. via the official website https://www.python.org

All required packages are listed on [requirements.txt](requirements.txt) -file. They can be installed using [pip](https://pip.pypa.io/en/stable/quickstart/). Pip should be installed alongside Python, so it's not needed to install that separately.

Install required packages:
```sh
pip install -r requirements.txt
```

*Note: Depending on the Python versions installed on your machine, you may need to add number 3 after the command to indicate you're using Python3 -environment. (`python` -> `python3` and `pip` -> `pip3`). Especially on macOS and Linux*


## Running the program

First create a configuration file.

The configuration should have following variables:
- `response_file`: Path to the file containing monitoring results. 
- `get_capabilities`: Path to the GetCapabilities-response file. 
- `output_raster_path`: Location where the output raster will be created.

See the example file [example.ini](sample_data/example.ini).


Call the script:

```sh
cd src
python Process.py <path to config file>
```


## General tips for contributing

### Pylint

Pylint is the linter for Python, that checks if the code contains some error. Pylint is added to the requirements file, so it should be installed when installing at the same time than other packages.

The easiest way to use linter is via your IDE or code editor when the problems are highlighted automatically.

Another option is to run Pylint via command line:

```sh
pylint -E src/
```

`-E` flag is used to list only real errors in the code. Other recommendations may be useful but there're definitely too much for us.

### Git

There're hundreds of ways to use Git. Maybe the easiest one is to use it via some GUI application, e.g. [GitHub Desktop](https://desktop.github.com) or your code editor.

Basic procedure to how use Git:
1. Before you start, call `git pull` to get the newest modifications of the repository created by others.
2. Make your modifications to the code. Remember to check them for the error e.g. with Pylint.
3. Use `git add` to stage those files you have changed. On the command line, `git status` helps.
4. `git commit` confirms the changes you've made. Write a commit message that describes what the specific commit does. E.g. *Add functionality to reproject raster files.* 
5. After commit, use `git push` to publish your modifications on the GitHub server so that others can see them.

**It's a good practise to make commits enough often, so it's easier to follow what has happened and when. In the other words, try to remember make a new commit after every specific feature or fix.**

If someone has made modications at the same time with you, you might get a message about a **merge conflict** when calling `git pull`or `git push`. That means that you have modified the same lines in the code, and Git can't decide which lines to keep. In that situation, check carefully the highlighted lines and decide how to combine those. Consult other developers if necessary. Validate the merge after you're ready, create a new commit about the fix and push it.

All development is done in the master branch, but if you're familiar with branches, it's fine to use also those. Just remember to merge your changes every now and then with the master in that case :slightly_smiling_face: 
