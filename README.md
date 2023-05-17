# Quiz Please Web Scraper

This project is a Python script that scrapes game data from [Quiz Please Yerevan](https://yerevan.quizplease.ru/schedule-past), processes it, and stores it in a Google Sheets document. The script only processes new games since its last run.

## Setup

1. Clone this repository to your local machine.
2. Install the required Python packages using the command `pip install -r requirements.txt`.
3. Make sure you have a `google_creds.json` file in the project root (follow the [gspread authentication guide](https://docs.gspread.org/en/latest/oauth2.html) to create one).
4. Run the script using the command `python quiz_please_scrapper.py`.

## How It Works

The script operates in several steps:

1. Loads the last processed game ID from a local JSON file.
2. Fetches game IDs from the Quiz Please website that are greater than the last processed game ID.
3. For each new game ID, it fetches and processes the game data from the website.
4. The processed data is then appended to a Google Sheets document.
5. The ID of the last processed game is saved locally for use in the next run.



## Logging

All events and errors are logged to a local text file (`log.txt`) for debugging and record-keeping purposes.

## What to Do with the Data
Whatever you want :) Here is the Tableau dashboard (in Russian) I created using the data scraped by this script: [Quiz Please Yerevan Dashboard](https://public.tableau.com/app/profile/dannyviz/viz/QuizPleaseYerevan/Teamstats).
