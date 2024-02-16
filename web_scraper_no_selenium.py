import requests
import time
import calendar
from datetime import datetime, timedelta
import re
import json
import pandas as pd

def station_location(type: int, date_from, date_to):
    '''
    Returns pandas DataFrame with stations info.
    Args:\n
    * param type: Station type.
    * param date_from: Start date
    * param date_to: End date
    '''
    # Send requst for location data
    postaje_link = f'https://meteo.arso.gov.si/webmet/archive/locations.xml?d1={date_from}&d2={date_to}&type={type}&%20lang=si'
    response = requests.get(postaje_link, timeout=None)
    response.encoding = 'utf-8'

    # Extract the content for location data
    pattern = re.search(r'points:{(.+)}', response.text, re.DOTALL)
    location_data = pattern.group(1)

    # RE for extracting station infos to list of tuples, one tuple for every station
    pattern = re.compile(r'_(\d+):{\s*name:"([^"]+)",\s*lon:([^,]+),\s*lat:([^,]+),\s*alt:(\d+),\s*type:(\d+)\s*}', re.UNICODE)
    location_data = re.findall(pattern, location_data)

    # Format the data into a dict
    formatted_data = {f"_{match[0]}": {"name": match[1], "lon": match[2], "lat": match[3], "alt": match[4], "type": match[5]} for match in location_data}

    # Conver dict to Pandas DataFrame
    df_location = pd.DataFrame.from_dict(formatted_data, orient='index')
    # Reset the index
    df_location.reset_index(inplace=True)
    df_location.columns = ["ID", "name", "lon", "lat", "alt", "type"]
    return df_location


def download_data(date_from, date_to, df_locations):
    '''
    Returns scraped data, ready for download.
    Args:\n
    * param date_from: Start date
    * param date_to: End date
    * param df_location: Pandas DataFrame with stations info.
    '''
    # List to store individual DataFrames from diferent stations
    data_list = []

    for index, row in df_locations.iterrows():
        # Initialize a dictionary to store values
        data_dict = {}
        # Extract station data
        row_items = list(row.items())
        station_id = row_items[0][1]
        station_name = row_items[1][1]
        station_lon = row_items[2][1]
        station_lat = row_items[3][1]
        station_type = row_items[5][1]
        print(f"Row index: {index} - Current station : {station_id} - {station_name}")
        
        # Send request for XML station data
        # Type 4 = Samodejne postaje
        if station_type == '4':
            data_link = f"https://meteo.arso.gov.si/webmet/archive/data.xml?lang=si&vars=12,19,13,20,14,26,2,21,15,23,16,24,17,27,4,28,18,29&group=halfhourlyData0&type=halfhourly&id={station_id[1:]}&d1={date_from}&d2={date_to}"
        else:
            data_link = f"https://meteo.arso.gov.si/webmet/archive/data.xml?lang=si&vars=35,56,38,57,36,58,37,59,43,60,46,61,40,62,33,63,85,65,88,66,89,67,41,68,80,69,81,70,47,71,48,72,49,74,50,75,51,77,52,78,53,83,54,82,55&group=dailyData2&type=daily&id={station_id[1:]}&d1={date_from}&d2={date_to}"
        response = requests.get(data_link, timeout=None)
        response.encoding = 'utf-8'

        # Extract the column names
        pattern = re.search(r'params:{(.+)}, points', response.text, re.DOTALL)
        column_names = pattern.group(1)
        column_names = re.sub(r'(\w+):', r'"\1":', column_names)
        # Convert to JSON
        column_names = "{" + column_names + "}"
        column_names = json.loads(column_names)
        column_names = {key : column_names[key]["l"] for key in column_names}

        # Extract the content
        pattern = re.search(r'points:{(.+)}', response.text, re.DOTALL)
        station_data = pattern.group(1)

        # Extract individual records (assuming each record starts with an underscore)
        records = re.findall(r'_(\d+):', station_data)

        # Process each record
        for record in records[1:]:
            # Extract the record content
            record_data = re.search(rf'_{record}:(\{{.*?\}})', station_data).group(1)

            # Add double quotes to keys
            record_data = re.sub(r'(\w+):', r'"\1":', record_data)

            # Convert to a json dictionary
            record_dict = json.loads(record_data)

            # Initialize a dictionary for the current record
            current_record = '_{}'.format(record)
            current_record_dict = {current_record: {}}

            # Iterate through features p0 to p17
            for i in range(len(column_names)):
                feature_key = 'p{}'.format(i)

                # If the feature is present in the record, add it to current_record
                if feature_key in record_dict:
                    current_record_dict[current_record][feature_key] = record_dict[feature_key]
                else:
                    # If the feature is missing, store np.nan
                    current_record_dict[current_record][feature_key] = pd.NA

            #Update data_dict with the current_record
            data_dict.update(current_record_dict)

        data_dict = pd.DataFrame.from_dict(data_dict, orient='index')
        data_dict.insert(0, 'record', data_dict.index)
        data_dict.insert(1, 'station_id', station_id)
        data_dict.insert(2, 'station_type', station_type)
        data_dict.insert(3, 'station_name', station_name)
        data_dict.insert(4, 'station_lon', station_lon)
        data_dict.insert(5, 'station_lat', station_lat)
        data_dict.insert(6, 'date_from', date_from)
        data_dict.insert(7, 'date_to', date_to)
        data_list.append(data_dict)

    # Concatenate the DataFrames in the list into a new DataFrame
    df = pd.concat(data_list, ignore_index=True)
    df = df.rename(columns=column_names)
    
    encoded_dates = []
    timestamp_values = [int(x[1:]) - int(df.loc[0, 'record'][1:]) for x in df['record']]
    # Calculate and display resulting dates
    reference_date = datetime.strptime(date_from+' 00:00', "%Y-%m-%d %H:%M")
    for timestamp_value in timestamp_values:
        delta = timedelta(minutes=timestamp_value)
        encoded_dates.append(reference_date + delta)
    df.insert(1, 'encoded_dates', encoded_dates)

    return df


if __name__ == '__main__':
    start_time = time.time()
    # Samodejne postaje - type = 4
    years = [2020, 2023]
    for year in years:
        for month in range(1, 13):
            # Get the first day of the month
            first_day = datetime(year, month, 1).strftime('%Y-%m-%d')
    
            # Calculate the last day of the month
            _, last_day_of_month = calendar.monthrange(year, month)
            last_day = datetime(year, month, last_day_of_month).strftime('%Y-%m-%d')
    
            # Calculate middle dates
            middle_date_1 = datetime(year, month, 15).strftime('%Y-%m-%d')
            middle_date_2 = datetime(year, month, 16).strftime('%Y-%m-%d')
    
            # Scrap data for first two weeks
            df_location = station_location(4, middle_date_1, middle_date_2)
            df = download_data(first_day, middle_date_1, df_location)
            file_name = f"samodejne_postaje_datefrom_{first_day}_dateto_{middle_date_1}.csv"
            download_path = ''
            df.to_csv(download_path + file_name , index=False)
            print(f"Finished : Date From = {first_day} , Date To = {middle_date_1}")
    
            # Scarp data for last two weeks
            df_location = station_location(4, middle_date_2, last_day)
            df = download_data(middle_date_2, last_day, df_location)
            file_name = f"samodejne_postaje_datefrom_{middle_date_2}_dateto_{last_day}.csv"
            df.to_csv(download_path + file_name , index=False)
            print(f"Finished : Date From = {middle_date_2} , Date To = {last_day}")

    # Padavinske postaje - type = 1
    date_from = '2020-01-01'
    date_to = '2023-12-31'
    df_location = station_location(1, date_from, date_to)
    df = download_data(date_from, date_to, df_location)
    file_name = f"padavinske_postaje_datefrom_{date_from}_dateto_{date_to}.csv"
    download_path = ''
    df.to_csv(download_path + file_name, index=False)
    print(f"Padavinske postaje : Date From = {date_from} , Date To = {date_to}")

    # Klimatoloske postaje - type = 2
    df_location = station_location(2, date_from, date_to)
    print(df_location)
    df = download_data(date_from, date_to, df_location)
    file_name = f"klimatoloske_postaje_datefrom_{date_from}_dateto_{date_to}.csv"
    df.to_csv(download_path + file_name, index=False)
    print(f"Klimatoloske postaje : Date From = {date_from} , Date To = {date_to}")

    # Glavne meteroloske postaje - type = 3
    df_location = station_location(3, date_from, date_to)
    print(df_location)
    df = download_data(date_from, date_to, df_location)
    file_name = f"glavne_meterosloske_postaje_datefrom_{date_from}_dateto_{date_to}.csv"
    df.to_csv(download_path + file_name, index=False)
    print(f"Glavne meteroloske postaje : Date From = {date_from} , Date To = {date_to}")

    print("Scraping finished!")
    end_time = time.time()
    print(f"Elapsed time in seconds = {end_time - start_time} - H:M:S = {str(timedelta(seconds=(end_time - start_time)))}")