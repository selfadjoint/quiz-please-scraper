import requests as req
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import gspread
from gspread_dataframe import set_with_dataframe
import logging
import json
import boto3

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s.%(msecs)03d %(levelname)s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Constants
MAIN_URL = 'https://yerevan.quizplease.ru/schedule-past'
GAME_URL_TEMPLATE = 'https://yerevan.quizplease.ru/schedule-past?page={}'
GAME_PAGE_URL_TEMPLATE = 'https://yerevan.quizplease.ru/game-page?id={}'
GOOGLE_SHEET_NAME = 'quiz-please-stats'  # Name of the Google Sheet to write the data to
GOOGLE_CREDENTIALS_PARAMETER = '/quizgame/google_credentials'  # Name of the parameter in Parameter Store

# Month translation dictionary
month_translation = {
    'января': '01',
    'февраля': '02',
    'марта': '03',
    'апреля': '04',
    'мая': '05',
    'июня': '06',
    'июля': '07',
    'августа': '08',
    'сентября': '09',
    'октября': '10',
    'ноября': '11',
    'декабря': '12',
}


def get_google_credentials():
    """
    Retrieves Google credentials from AWS Systems Manager Parameter Store.
    """
    ssm = boto3.client('ssm')
    parameter_name = GOOGLE_CREDENTIALS_PARAMETER

    try:
        parameter = ssm.get_parameter(Name=parameter_name, WithDecryption=True)
        return parameter['Parameter']['Value']
    except Exception as e:
        logging.error(f"Failed to retrieve Google credentials: {e}")
        return None


def load_last_processed_game_id():
    try:
        gc = gspread.service_account_from_dict(json.loads(get_google_credentials()))
        sheet = gc.open(GOOGLE_SHEET_NAME).sheet1

        # Assuming game IDs are in the first column, get all values in that column
        game_id_column = sheet.col_values(1)
        if not game_id_column:
            logging.info('Google Sheet is empty')
            return 0

        logging.info(f"Last game ID in Google Sheet: {game_id_column[-1]}")
        return int(game_id_column[-1])
    except Exception as e:
        logging.error(f"Failed to load last game ID from Google Sheets: {e}")
        raise


def get_game_ids(_last_game_id):
    """
    Fetches new game IDs from the website.
    """
    try:
        main_page = req.get(MAIN_URL)
        main_soup = BeautifulSoup(main_page.content, 'html.parser')
        game_page_counter = len(main_soup.find('ul', class_='pagination').find_all('li')) - 2

        game_ids = []
        for _page in range(1, game_page_counter + 1):
            games_url = GAME_URL_TEMPLATE.format(_page)
            games_page = req.get(games_url)
            games_soup = BeautifulSoup(games_page.content, 'html.parser')
            page_game_ids = [int(re.findall('id=(\d+)', str(x))[0]) for x in
                             games_soup.find_all("div", class_='game-buttons available')]

            # Filter out game IDs that are not greater than the last game ID
            new_game_ids = [game_id for game_id in page_game_ids if game_id > _last_game_id]

            if not new_game_ids:
                # If there are no new game IDs on this page, we can stop fetching more pages
                break

            game_ids.extend(new_game_ids)
        return game_ids[::-1]
    except Exception as e:
        logging.error(f"Failed to get game IDs: {e}")
        return []


def process_game(_game_id):
    """
    Fetches and processes data for a single game.
    """
    game_url = GAME_PAGE_URL_TEMPLATE.format(_game_id)
    page = req.get(game_url)
    soup = BeautifulSoup(page.content, 'html.parser')
    game_attrs = soup.find("div", class_='game-heading-info').find_all('h1')

    date = soup.find_all('div', class_='game-info-column')[2].find('div', class_='text').text.split()
    date[0] = '0' + date[0] if len(date[0]) == 1 else date[0]
    date[1] = month_translation[date[1]]

    # Some hardcode for the correct game year determination. Needs to be updated every year
    if _game_id < 49999:
        date += ' 2022'
    elif _game_id < 69919:
        date += ' 2023'
    else:
        date += ' 2024'

    date = '-'.join(date[::-1])

    table = pd.read_html(page.text)
    df = table[0].filter(regex='аунд|есто|азвание', axis=1).copy()
    df.columns = df.columns.str.capitalize()
    df['Категория'] = soup.find("div", class_="game-tag").text.strip()
    df['Название игры'] = re.findall('.+(?=\sY)', game_attrs[0].text)[0]
    df['Номер игры'] = game_attrs[1].text[1:]
    df['ID'] = _game_id
    df['Дата'] = date
    df = df.melt(id_vars=['ID', 'Дата', 'Название команды', 'Категория', 'Название игры', 'Номер игры', 'Место'],
                 var_name='Раунд', value_name='Очки')  # From wide to long table
    return df


def process_all_games(_game_ids):
    """
    Processes data for all new games.
    """
    data = []
    for _id in _game_ids:
        try:
            df = process_game(_id)
            data.append(df)
            time.sleep(1)
        except Exception as e:
            logging.error(f"Failed to process game ID {_id}: {e}")
    return pd.concat(data)


def load_into_sheets(_df):
    """
    Loads the processed data into Google Sheets.
    """
    try:
        google_creds_json = get_google_credentials()
        if google_creds_json is None:
            raise Exception("Google credentials could not be loaded")

        # Use credentials to authorize with gspread
        gc = gspread.service_account_from_dict(json.loads(google_creds_json))
        wks = gc.open(GOOGLE_SHEET_NAME).sheet1
        if not len(wks.get_all_values()):  # If the sheet is empty, write the DataFrame with headers
            set_with_dataframe(worksheet=wks, dataframe=_df, include_index=False, include_column_header=True,
                               resize=True)
        else:  # If the sheet is not empty, append the DataFrame without headers
            data_to_append = _df.astype(str).values.tolist()  # Convert DataFrame to list of lists
            wks.append_rows(data_to_append)  # Append the data to the sheet
    except Exception as e:
        logging.error(f"Failed to load data into Google Sheets: {e}")
        raise


def lambda_handler(event, context):
    """
    The main function that runs the entire process.
    """
    last_game_id = load_last_processed_game_id()
    new_game_ids = get_game_ids(last_game_id)
    logging.info(f'Processing {len(new_game_ids)} new games')
    if new_game_ids:
        df = process_all_games(new_game_ids)
        df['Название команды'] = df['Название команды'].str.strip().str.upper()
        load_into_sheets(df)
        logging.info(f'Updated: {len(new_game_ids)} games')
    else:
        logging.info('No new games to process')
