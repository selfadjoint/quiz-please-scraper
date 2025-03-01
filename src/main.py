import requests as req
from bs4 import BeautifulSoup
import re
import time
import gspread
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
    Fetches and processes data for a single game without using pandas.
    Returns a list of dictionaries, each representing one melted row.
    """

    # Fetch the game page and parse with BeautifulSoup
    game_url = GAME_PAGE_URL_TEMPLATE.format(_game_id)
    page = req.get(game_url)
    soup = BeautifulSoup(page.content, 'html.parser')

    # Get game header attributes
    game_heading = soup.find("div", class_="game-heading-info")
    game_attrs = game_heading.find_all("h1") if game_heading else []

    # Process date using zfill and the month translation dictionary
    info_columns = soup.find_all("div", class_="game-info-column")
    if len(info_columns) >= 3:
        date_text = info_columns[2].find("div", class_="text").get_text(strip=True).split()
    else:
        date_text = ["1", "января"]
    day = date_text[0].zfill(2)
    month = month_translation.get(date_text[1], date_text[1])
    if _game_id < 49999:
        year = "2022"
    elif _game_id < 69919:
        year = "2023"
    elif _game_id < 93630:
        year = "2024"
    else:
        year = "2025"
    full_date = f"{year}-{month}-{day}"

    # Parse the first HTML table on the page.
    table_tag = soup.find("table")
    if not table_tag:
        logging.error("No table found in the game page.")
        return []

    # Extract headers: if there's a thead, use it; otherwise use the first row.
    headers = []
    thead = table_tag.find("thead")
    if thead:
        header_row = thead.find("tr")
        headers = [th.get_text(strip=True).capitalize() for th in header_row.find_all(["th", "td"])]
    else:
        first_tr = table_tag.find("tr")
        headers = [cell.get_text(strip=True).capitalize() for cell in first_tr.find_all(["th", "td"])]

    # Filter headers to only include those matching the regex (e.g. 'аунд', 'есто', 'азвание')
    regex = re.compile(r"(аунд|есто|азвание)", re.IGNORECASE)
    filtered_indices = [i for i, h in enumerate(headers) if regex.search(h)]
    # We'll use the original header names (capitalized) when extracting cells.

    # Extract data rows (skip header row if no thead)
    data_rows = []
    tbody = table_tag.find("tbody")
    rows = tbody.find_all("tr") if tbody else table_tag.find_all("tr")[1:]
    for row in rows:
        cells = row.find_all(["td", "th"])
        row_data = {}
        for i in filtered_indices:
            if i < len(cells):
                cell_text = cells[i].get_text(strip=True)
            else:
                cell_text = ""
            row_data[headers[i]] = cell_text.strip().upper()
        data_rows.append(row_data)

    # Add additional columns from page content
    category = soup.find("div", class_="game-tag").get_text(strip=True) if soup.find("div", class_="game-tag") else ""
    game_name = ""
    if game_attrs and len(game_attrs) > 0:
        match = re.findall(r".+(?=\sY)", game_attrs[0].get_text(strip=True))
        if match:
            game_name = match[0]
    game_number = game_attrs[1].get_text(strip=True)[1:] if len(game_attrs) > 1 else ""

    additional_data = {
        "Категория": category,
        "Название игры": game_name,
        "Номер игры": game_number,
        "ID": _game_id,
        "Дата": full_date,
    }
    for row in data_rows:
        row.update(additional_data)

    # Define id_vars that will remain unchanged during the melt operation
    id_vars = ["ID", "Дата", "Название команды", "Категория", "Название игры", "Номер игры", "Место"]

    # Manually perform the melt: for each row, for each key not in id_vars,
    # create a new row with the id_vars plus "Раунд" (the original column name) and "Очки" (its value)
    melted = []
    for row in data_rows:
        for key, value in row.items():
            if key not in id_vars:
                new_row = {k: row.get(k, "") for k in id_vars}
                new_row["Раунд"] = key
                new_row["Очки"] = value
                melted.append(new_row)

    return melted


def load_into_sheets(data):
    """
    Loads the processed data (list of dictionaries) into Google Sheets.
    If the sheet is empty, it writes a header row (derived from the dictionary keys) and the data.
    Otherwise, it appends only the new rows.
    """
    try:
        google_creds_json = get_google_credentials()
        if google_creds_json is None:
            raise Exception("Google credentials could not be loaded")

        # Authorize with gspread using the provided credentials
        gc = gspread.service_account_from_dict(json.loads(google_creds_json))
        wks = gc.open(GOOGLE_SHEET_NAME).sheet1

        # Get existing values from the sheet
        existing_values = wks.get_all_values()

        if not existing_values:
            # Sheet is empty: prepare header from keys and full data rows
            header = list(data[0].keys()) if data else []
            rows = [header]
            for entry in data:
                row = [str(entry.get(col, "")) for col in header]
                rows.append(row)
            # Update the sheet starting at A1
            wks.update('A1', rows)
        else:
            # Sheet is not empty: assume header is already present.
            # Use the existing header to order the new data rows.
            header = existing_values[0]
            rows = []
            for entry in data:
                row = [str(entry.get(col, "")) for col in header]
                rows.append(row)
            # Append the new rows to the sheet.
            wks.append_rows(rows)
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
        for game in new_game_ids:
            game_stats = process_game(game)
            load_into_sheets(game_stats)
        logging.info(f'Updated: {len(new_game_ids)} games')
    else:
        logging.info('No new games to process')
