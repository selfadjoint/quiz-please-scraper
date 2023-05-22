import requests as req
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import dateparser
import gspread
from gspread_dataframe import set_with_dataframe
import logging
import json

logging.basicConfig(filename='log.txt', level=logging.INFO, format='%(asctime)s.%(msecs)03d %(levelname)s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

MAIN_URL = 'https://yerevan.quizplease.ru/schedule-past'
GAME_URL_TEMPLATE = 'https://yerevan.quizplease.ru/schedule-past?page={}'
GAME_PAGE_URL_TEMPLATE = 'https://yerevan.quizplease.ru/game-page?id={}'
LAST_GAME_ID_FILE = 'last_game_id.json'
GOOGLE_SHEET_NAME = 'quiz-please-stats'
GOOGLE_CREDENTIALS_FILE = 'google_creds.json'  # JSON file with Google credentials


def save_last_game_id(_game_id):
    """
    Saves the last game ID to a file.
    """
    with open(LAST_GAME_ID_FILE, 'w') as f:
        json.dump({'last_game_id': _game_id}, f)


def load_last_game_id():
    """
    Loads the last game ID from a file.
    """
    try:
        with open(LAST_GAME_ID_FILE, 'r') as f:
            return json.load(f).get('last_game_id', 0)
    except FileNotFoundError:
        return 0


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

    date = soup.find_all("div", class_='game-info-column')[1].find("div", class_='text').text
    if _game_id < 49999:
        # Some hardcode for the correct game year determination. Needs to be updated every year
        date = dateparser.parse(date + ' 2022')
    else:
        date = dateparser.parse(date + ' 2023')

    table = pd.read_html(page.text)
    df = table[0].filter(regex='аунд|есто|азвание', axis=1).copy()
    df.columns = df.columns.str.capitalize()
    df['Категория'] = soup.find("div", class_="game-tag").text.strip()
    df['Название игры'] = re.findall('.+(?=\sY)', game_attrs[0].text)[0]
    df['Номер игры'] = game_attrs[1].text[1:]
    df['ID'] = _game_id
    df['Дата'] = date
    df = df.melt(id_vars=['ID', 'Дата', 'Название команды', 'Категория', 'Название игры', 'Номер игры', 'Место'],
                 var_name='Раунд', value_name='Очки') # From wide to long table
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
        gc = gspread.service_account(filename=GOOGLE_CREDENTIALS_FILE)
        wks = gc.open(GOOGLE_SHEET_NAME).sheet1
        if not len(wks.get_all_values()):  # If the sheet is empty, write the DataFrame with headers
            set_with_dataframe(worksheet=wks, dataframe=_df, include_index=False, include_column_header=True,
                               resize=True)
        else:  # If the sheet is not empty, append the DataFrame without headers
            data_to_append = _df.astype(str).values.tolist()  # Convert DataFrame to list of lists
            wks.append_rows(data_to_append)  # Append the data to the sheet
    except Exception as e:
        logging.error(f"Failed to load data into Google Sheets: {e}")


def main():
    """
    The main function that runs the entire process.
    """
    last_game_id = load_last_game_id()
    new_game_ids = get_game_ids(last_game_id)
    logging.info(f'Processing {len(new_game_ids)} new games')
    if new_game_ids:
        df = process_all_games(new_game_ids)
        df['Название команды'] = df['Название команды'].str.strip().str.upper()
        load_into_sheets(df)
        save_last_game_id(max(new_game_ids))
        logging.info(f'Updated: {len(new_game_ids)} games')
    else:
        logging.info('No new games to process')


if __name__ == "__main__":
    main()
