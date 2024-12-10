# Pull Request File Search

This script uses the GitHub API to search for pull requests that have modified a specific file in a given repository. It allows users to filter pull requests by their status (open or all) and optionally by a date range.

This is useful when you want to search for a specific file that was modified by a pull request that is not merged. GitHub's UI does not provide an easy way to specify changed files as part of the search criteria for pull requests, but this script can search through a large number of pull requests within a matter of seconds.

## Features

- Fetch pull requests from a specified GitHub repository.
- Filter pull requests by status (open or all).
- Optionally filter pull requests by a date range.
- Search for a specific file within the pull requests.
- Display the URLs of pull requests that modified the specified file.

## Requirements

- Python 3.7+
- The following Python packages (listed in `requirements.txt`):
  - certifi==2024.8.30
  - charset-normalizer==3.4.0
  - idna==3.10
  - requests==2.32.3
  - urllib3==2.2.3

## Setup

1. Clone the repository:

    ```sh
    git clone <https://github.com/pknoche/pull-request-file-search>
    cd <repository-directory>
    ```

2. Install the required packages:

    ```sh
    pip install -r requirements.txt
    ```

3. Copy or rename `config_template.ini` to `config.ini` and fill in the required configuration values:

    ```ini
    [GITHUB]
    API_ROOT_ENDPOINT=https://api.github.com
    OWNER=<your-github-username-or-organization>
    REPO=<your-repository-name>

    [AUTHENTICATION]
    GITHUB_TOKEN=<your-github-personal-access-token>
    ```

## Usage

Run the script:

```sh
python main.py
```

## Example

```text
$ python main.py
Enter full path of file to search for in pull requests: src/example.py

Would you like to search just open pull requests or all pull requests? (open/all): all

Do you want to filter by date range? (yes/no): yes

Enter the start date (format: "mm-dd-yy"): 01-01-23
Enter the end date (format: "mm-dd-yy"): 12-31-23

Processing all pull requests opened between 2023-01-01 00:00:00 and 2023-12-31 00:00:00...
Processing PR #123
Processing PR #124
Processing PR #125
Reached pull requests outside the date range. Stopping.

Pull requests that modified src/example.py:
https://github.com/your-repo/pull/123
https://github.com/your-repo/pull/125

Searched 3 pull requests and 20 files.

Search finished in 3.94 seconds.

Would you like to search again? (yes/no): 
```

## License

This project is licensed under the terms of the GNU General Public License v3.0.

See [LICENSE](LICENSE) for more information.
