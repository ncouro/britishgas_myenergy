#!/usr/bin/env python2.7

import argparse
import calendar
from datetime import datetime
import logging

from britishgas_myenergy import client

# First to download the history from. The response to the request
# will contain every day from the 1 January of this year.
BEGIN_YEAR = 2015

# Name of output CSV file containing gas data
GAS_FILENAME = "myenergy_gas.csv"

# Name of output CSV file containing electricity data
ELEC_FILENAME = "myenergy_electricity.csv"


def make_csv_row(consumption_data):
    """Make a CSV row string from a consumption_data key"""
    return ', '.join((consumption_data['from'],
            str(consumption_data['energy']),
            str(consumption_data['cost']),
            str(consumption_data['partial']),
            str(consumption_data['estimated']['energy']),
            str(consumption_data['estimated']['cost'])))


def save_as_csv(consumption_history, filename):
    """Save the "consumption_data" reponse as a CSV file
    Args:
        consumption_history (dict): GraphQL response
        filename (str): CSV file name
    """
    with open(filename, 'w') as f:
        for data in consumption_history:
            f.write(make_csv_row(data) + '\n')


def iterate_month_range(begin_datetime, end_datetime):
    """Iterate between two datetimes and produce
    intervals (first day of month, last day of month)
    Args:
        begin_datetime (datetime.datetime) : date to iterate from
        end_datetime (datetime.datetime) : date to iterate to

    Yields:
        (datetime.datetime, datetime.datetime): pair of
        first day of the month and last day of the month.
    """
    month_iter = begin_datetime.month
    MONTHS_IN_YEAR = 12

    while True:
        year = begin_datetime.year + month_iter // MONTHS_IN_YEAR
        month = month_iter % MONTHS_IN_YEAR + 1
        # Iterate until we've reached the end datetime
        if month > end_datetime.month and year >= end_datetime.year:
            break

        NB_DAYS_IDX = 1
        yield (datetime(year, month, 1, 0, 0, 0),
               datetime(year, month,
                        calendar.monthrange(year, month)[NB_DAYS_IDX],
                        23, 59, 59))

        month_iter = month_iter + 1


def fetch_consumption_history(username, password, account_number):
    """Get the consumption history from the hardcoded time origin to
    the present time.
    Args:
        username (str): British Gas / myenergy user name (e.g. email address)
        password (str): British Gas / myenergy account password
        account_number (int): British Gas / myenergy account number
    Returns:
        "consumption_data" GraphQL response.
    """
    login_response, session_cookies, graphql_token = client.login(
        username, password, str(account_number))
    gql_client = client.get_graphql_client(
        login_response, session_cookies, graphql_token)

    # This returns a dictionary with only one key 'consumptionRange'
    all_fuels_history = []
    first_day = datetime(BEGIN_YEAR, 1, 1, 0, 0, 0)
    last_day = datetime.now()

    for (first_day_month, last_day_month) in iterate_month_range(first_day, last_day):
        month_query = client.daily_history_query(
            first_day_month,
            last_day_month)

        # The server returns an error if the energy data is not available
        # during a given time period. There may be a nicer way to handle
        # this.
        try:
            consumption_history = gql_client.execute(month_query)
            all_fuels_history.extend(consumption_history['consumptionRange'])
        except Exception:
            logging.warn(
                'Could not retrieve information for period {0} to {1}'.format(
                first_day_month.isoformat(), last_day_month.isoformat()))

    return all_fuels_history


def main():
    """Entry point"""
    parser = argparse.ArgumentParser(
        description='Download British Gas myenergy data')
    parser.add_argument('username', type=str,
                        help='Account username (or email address)')
    parser.add_argument('password', type=str,
                        help='Account password')
    parser.add_argument('account_number', type=int,
                        help='Account number')

    args = parser.parse_args()

    # Download data
    all_fuels = fetch_consumption_history(
        args.username, args.password, args.account_number)

    # Remove empty items
    valid_data = [_ for _ in all_fuels if not _['empty']]
    gas_history = [_ for _ in valid_data if _['fuel'] == 'gas']
    elec_history = [_ for _ in valid_data if _['fuel'] == 'electricity']

    # Save data
    save_as_csv(gas_history, GAS_FILENAME)
    save_as_csv(elec_history, ELEC_FILENAME)


if __name__ == '__main__':
    main()
