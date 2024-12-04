import requests
import configparser
import os
import sys
from datetime import datetime

def main():
    # Determine environment that script is executing in and read config file
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(application_path, 'config.ini')

    if not os.path.exists(config_path):
        print(f'Error: Configuration file "config.ini" not found in {application_path}')
        input('Press Enter to exit...')
        sys.exit(1)

    config = configparser.ConfigParser()
    config.read(config_path)

    # Config parameters
    GITHUB_ENDPOINT = config['GITHUB'].get('API_ROOT_ENDPOINT')
    OWNER = config['GITHUB'].get('OWNER')
    REPO = config['GITHUB'].get('REPO')
    GITHUB_TOKEN = config['AUTHENTICATION'].get('GITHUB_TOKEN')
    HEADERS = {
        'Accept': 'application/vnd.github+json',
        'Authorization': f'Bearer {GITHUB_TOKEN}'
        }
    RESULTS_PER_PAGE = 100

    if not GITHUB_TOKEN:
        print('Error: missing GitHub token in config.ini')
        input('Press Enter to exit...')
        sys.exit(1)

    # Get and verify user inputs
    target_file = input('Enter full path of file to search for in pull requests: ')

    while True:
        pr_status = input('\nWould you like to search just open pull requests or all pull requests? (open/all): ').strip().lower()
        if pr_status == 'open' or pr_status == 'all':
            break
        else:
            print('Invalid status entered. Specify "open" or "all".')

    date_filtering = False
    START_DATE = None
    END_DATE = None

    if pr_status == 'open':
        print('\nProcessing all open PRs...')
    else:
        while True:
            filter_choice = input('\nDo you want to filter by date range? (yes/no): ').strip().lower()
            if filter_choice == 'yes' or filter_choice == 'no':
                break
            else:
                print('Enter "yes" or "no"')

        if filter_choice == 'yes':
            date_filtering = True
            date_format = '%m-%d-%y'
            while True:
                start_date_input = input(f'\nEnter the start date (format: "mm-dd-yy"): ').strip()
                end_date_input = input(f'Enter the end date (format: "mm-dd-yy"): ').strip()
                try:
                    START_DATE = datetime.strptime(start_date_input, date_format)
                    END_DATE = datetime.strptime(end_date_input, date_format)

                    if START_DATE > END_DATE:
                        print('Start date cannot be after end date. Please enter the dates again.')
                        continue
                    print(f'\nProcessing all pull requests opened between {START_DATE} and {END_DATE}...')
                    break
                except ValueError as ve:
                    print(f'Invalid date format: {ve}. Please enter the dates again.')
        else:
            print('\nProcessing all PRs with no date filtering...')

    # Begin processing PRs
    pull_requests_with_file = []
    page = 1
    while True:
        # Step 1: Get pull requests
        pulls_url = f'{GITHUB_ENDPOINT}/repos/{OWNER}/{REPO}/pulls'
        params = {'state': pr_status, 
                'per_page': RESULTS_PER_PAGE, 
                'page': page,
                'sort': 'created',
                'direction': 'desc'}

        pulls_response = requests.get(pulls_url, headers=HEADERS, params=params)

        # Check for response errors
        if pulls_response.status_code != 200:
            print(f'Error fetching pull requests: {pulls_response.status_code}')
            print(f'Response Content: {pulls_response.text}')
            input('Press Enter to exit...')
            sys.exit(1)

        pulls = pulls_response.json()

        if not pulls:
            break  # No more pull requests

        stop_processing = False

        for pr in pulls:
            # Only process PRs that fall within specified date range
            if date_filtering:
                pr_created_at = datetime.strptime(pr['created_at'], '%Y-%m-%dT%H:%M:%SZ')

                if pr_created_at > END_DATE:
                    continue
                elif pr_created_at < START_DATE:
                    # Since pull requests are sorted by creation date descending,
                    # we can stop processing further pull requests
                    print('Reached pull requests outside the date range. Stopping.')
                    stop_processing = True
                    break

            pull_number = pr['number']
            pull_url = pr['html_url']
            files_page = 1

            while True:
                # Step 2: Get files changed in the pull request
                print(f'Processing PR #{pull_number}')
                files_url = f'{GITHUB_ENDPOINT}/repos/{OWNER}/{REPO}/pulls/{pull_number}/files'
                files_params = {'per_page': RESULTS_PER_PAGE, 'page': files_page}
                files_response = requests.get(files_url, headers=HEADERS, params=files_params, verify=True)

                # Check for HTTP errors
                if files_response.status_code != 200:
                    print(f'Error fetching files for PR #{pull_number}: {files_response.status_code}')
                    print(f'Response Content: {files_response.text}')
                    input('Press Enter to exit...')
                    sys.exit(1)
                
                files = files_response.json()
                if not files:
                    break  # No more files in this pull request  

                # Step 3: Check if the specified file was changed
                file_found = False
                for file in files:
                    if file['filename'] == target_file:
                        pull_requests_with_file.append(pull_url)
                        file_found = True  # No need to check more files in this pull request
                        break

                if file_found:
                    break  # No need to check more pages of files in this pull request
                
                # Continue to the next page of files
                if 'next' in files_response.links:
                    files_page += 1
                else:
                    break  # No more pages of files

        if stop_processing:
            break  # break out of the main loop

        # Continue to the next page of pull requests
        if 'next' in pulls_response.links:
            page += 1
        else:
            break  # no more pages of pull requests
        
    # Output the list of pull requests found with the specified file changed
    if not pull_requests_with_file:
        print('\nNo pull requests found that modified the specified file.')
    else:
        print(f'\nPull requests that modified {target_file}:')
        for pull_url in pull_requests_with_file:
            print(pull_url)


if __name__ == '__main__':
    while True:
        main()
        while True:
            search_again = input('\nWould you like to search again? (yes/no): ').strip().lower()
            if search_again in ['yes', 'no']:
                break
            print('Invalid input. Please type "yes" or "no".')
        if search_again == 'no':
            sys.exit(0)
        print()
