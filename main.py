#     This file is part of the Pull Request File Search project.
#     Copyright (C) 2024  Philipp Knoche
#
#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program.  If not, see <https://www.gnu.org/licenses/>.


import requests
import configparser
import os
import sys
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

class PullRequestAnalyzer:
    def __init__(self):
        self.RESULTS_PER_PAGE = 100
        self.pull_requests_with_file = []
        self.pull_requests_searched = 0
        self.files_searched = 0

    def read_config(self):
        '''Reads and validates the configuration file config.ini'''
        if getattr(sys, 'frozen', False):
            application_path = os.path.dirname(sys.executable)
        else:
            application_path = os.path.dirname(os.path.abspath(__file__))

        config_path = os.path.join(application_path, 'config.ini')
        if not os.path.exists(config_path):
            raise FileNotFoundError(f'Configuration file "config.ini" not found in {application_path}')

        config = configparser.ConfigParser()
        config.read(config_path)

        # Extract configuration parameters
        try:
            self.GITHUB_ENDPOINT = config['GITHUB'].get('API_ROOT_ENDPOINT')
            self.OWNER = config['GITHUB'].get('OWNER')
            self.REPO = config['GITHUB'].get('REPO')
            self.GITHUB_TOKEN = config['AUTHENTICATION'].get('GITHUB_TOKEN')
        except KeyError as e:
            raise KeyError(f'Missing configuration section: {e} in config.ini')
        
        if not self.GITHUB_ENDPOINT:
            raise ValueError('GITHUB_ENDPOINT is missing in config.ini')
        if not self.OWNER:
            raise ValueError('OWNER is missing in config.ini')
        if not self.REPO:
            raise ValueError('REPO is missing in config.ini')
        if not self.GITHUB_TOKEN:
            raise ValueError('GITHUB_TOKEN is missing in config.ini')

        self.HEADERS = {
            'Accept': 'application/vnd.github+json',
            'Authorization': f'Bearer {self.GITHUB_TOKEN}'
            }

    def get_user_inputs(self):
        '''Prompts the user for inputs and validates them.'''
        self.target_file = input('Enter full path of file to search for in pull requests: ')

        while True:
            pr_status = input('\nWould you like to search just open pull requests or all pull requests? (open/all): ').strip().lower()
            if pr_status == 'open' or pr_status == 'all':
                self.pr_status = pr_status
                break
            else:
                print('Invalid status entered. Specify "open" or "all".')

        self.date_filtering = False
        self.START_DATE = None
        self.END_DATE = None

        if self.pr_status == 'all':
            while True:
                filter_choice = input('\nDo you want to filter by date range? (yes/no): ').strip().lower()
                if filter_choice in ['yes', 'no']:
                    break
                else:
                    print('Enter "yes" or "no"')

            if filter_choice == 'yes':
                self.date_filtering = True
                date_format = '%m-%d-%y'
                while True:
                    start_date_input = input(f'\nEnter the start date (format: "mm-dd-yy"): ').strip()
                    end_date_input = input(f'Enter the end date (format: "mm-dd-yy"): ').strip()
                    try:
                        self.START_DATE = datetime.strptime(start_date_input, date_format)
                        self.END_DATE = datetime.strptime(end_date_input, date_format)
                        if self.START_DATE > self.END_DATE:
                            print('Start date cannot be after end date. Please enter the dates again.')
                            continue
                        print(f'\nProcessing all pull requests opened between {self.START_DATE} and {self.END_DATE}...')
                        break
                    except ValueError as ve:
                        print(f'Invalid date format: {ve}. Please enter the dates again.')
            else:
                print('\nProcessing all PRs with no date filtering...')
        else: print('\nProcessing all open PRs...')

    def fetch_pull_requests(self):
        '''Generator function to fetch all pull requests with pagination'''
        page = 1
        while True:
            pulls_url = f'{self.GITHUB_ENDPOINT}/repos/{self.OWNER}/{self.REPO}/pulls'
            params = {
                'state': self.pr_status, 
                'per_page': self.RESULTS_PER_PAGE, 
                'page': page,
                'sort': 'created',
                'direction': 'desc'
            }

            # Make API request and check for errors
            response = requests.get(pulls_url, headers=self.HEADERS, params=params, verify=True)
            if response.status_code != 200:
                raise Exception(f'Error fetching pull requests: {response.status_code}, {response.text}')
            
            pulls = response.json()
            if not pulls:
                break  # No more pull requests
            yield from pulls

            if 'next' in response.links:
                page += 1
            else:
                break

    def fetch_pr_files(self, pull_number):
        '''Generator function to fetch files in pull request with pagination'''
        page = 1
        while True:
            files_url = f'{self.GITHUB_ENDPOINT}/repos/{self.OWNER}/{self.REPO}/pulls/{pull_number}/files'
            params = {'per_page': self.RESULTS_PER_PAGE, 'page': page}

            # Make API request and check for errors
            response = requests.get(files_url, headers=self.HEADERS, params=params, verify=True)
            if response.status_code != 200:
                raise Exception(f'Error fetching files for PR #{pull_number}: {response.status_code}, {response.text}')    
                
            files = response.json()
            if not files:
                break  # No more files in this pull request
            yield from files

            if 'next' in response.links:
                page += 1
            else:
                break

    def process_pull_requests(self):
        '''Processes pull requests and checks for the target file asynchronously'''
        self.start_time = time.time()
        file_request_futures=[]
        with ThreadPoolExecutor() as executor:
            for pr in self.fetch_pull_requests():
                # Only process PRs that fall within specified date range
                if self.date_filtering:
                    pr_created_at = datetime.strptime(pr['created_at'], '%Y-%m-%dT%H:%M:%SZ')
                    if pr_created_at > self.END_DATE:
                        continue
                    elif pr_created_at < self.START_DATE:
                        # Since pull requests are sorted by creation date descending,
                        # we can stop processing further pull requests
                        print('Reached pull requests outside the date range. Stopping.')
                        break

                pull_number = pr['number']
                pull_url = pr['html_url']
                self.pull_requests_searched += 1
                print(f'Processing PR #{pull_number}')
                file_request_futures.append(executor.submit(self.read_files, pull_number, pull_url))
            
            # Display error message for any pull requests we were unable to fetch files for 
            # and continue processing
            for future in file_request_futures:
                try:
                    future.result()
                except Exception as e:
                    print(e)

    def read_files(self, pull_number, pull_url):
        '''Fetch PR files and determine if specified file was changed'''
        for file in self.fetch_pr_files(pull_number):
            self.files_searched += 1
            if file['filename'] == self.target_file:
                self.pull_requests_with_file.append(pull_url)
                break # No need to check more files in this pull request

    def display_results(self):
        if not self.pull_requests_with_file:
            print(f'\nNo pull requests found that modified {self.target_file}')
        else:
            print(f'\nPull requests that modified {self.target_file}:')
            for pull_url in self.pull_requests_with_file:
                print(pull_url)
        print(f'\n\nSearched {analyzer.pull_requests_searched} pull requests and {analyzer.files_searched} files.')

    def run(self):
        '''Main method to run program'''
        try:
            self.read_config()
            self.get_user_inputs()
            self.process_pull_requests()
            self.display_results()
        except Exception as e:
            print(f'Error: {e}')
            input('Press Enter to exit...')
            sys.exit(1)

if __name__ == '__main__':
    while True:
        analyzer = PullRequestAnalyzer()
        analyzer.run()
        end_time = time.time()
        print(f'\nSearch finished in {end_time - analyzer.start_time:.2f} seconds.')
        while True:
            search_again = input('\nWould you like to search again? (yes/no): ').strip().lower()
            if search_again in ['yes', 'no']:
                break
            print('Invalid input. Please type "yes" or "no".')
        if search_again == 'no':
            sys.exit(0)
        print()
