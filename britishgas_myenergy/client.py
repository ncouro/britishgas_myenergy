from lxml import html
import logging
import requests

from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

logging.basicConfig()


# British Gas account login page
LOGIN_PAGE_URL = 'https://www.britishgas.co.uk/apps/britishgas/components/OAMLogin/POST.servlet'

# My Energy overview page
MYENERGY_PAGE_URL = 'https://www.britishgas.co.uk/apps/britishgas/components/PEEAEnergyUsage/GET.servlet'

# URL to GraphQL server for energy data
MYENERGY_GRAPHQL_URL = 'https://www.britishgas.co.uk/myenergy_prod/me-api/graphql'

# GraphQL request time out (seconds)
TIMEOUT_S = 60


def daily_history_query(first_datetime, last_datetime):
    """Build the GraqhQL query to retrieve  daily data between two dates.
    Args:
        first_datetime (datetime.datetime): beginning of data series
        last_datetime (datetime.datetime): end of date series
    Returns: (dict)
    """
    day_range = 'from:"{0:s}.000Z", to:"{1:s}.999Z"'.format(
        first_datetime.isoformat(),
        last_datetime.isoformat())

    # The "half_hourly" granularity is not visible yet.
    return gql('''query DetailedHistory {
        consumptionRange(granularity:daily, %s) {
            from
            partial
            estimated {
                cost
                energy
            }
            empty
            zoomable
            tou
            cost(costUnit:pounds)
            energy(energyUnit:kwh)
            fuel
            daysWithData
        }
    }''' % day_range)


def login(username, password, account_number):
    """Perform authentication of myenergy account

    Returns (requests.Response, requests.CookieJar, string)
    """
    # Authenticate
    with requests.Session() as s:
        data = {
            'emailAddress': username,
            'password': password,
            'nextPage': '/content/britishgas/youraccount/oam-login/account-overview.html',
            'currentPage': '/content/britishgas/youraccount/oam-login/smartenergylogin.html',
            'redirectToPreviousPage': 'false',
            'showInterstialPage': 'false'}

        login_page_response = s.post(
            LOGIN_PAGE_URL,
            data=data,
            auth=requests.auth.HTTPDigestAuth(username, password),
            allow_redirects=True,
            headers={
                'User-agent': 'Mozilla/5.0',
            })
        login_page_response.raise_for_status()

        # Retrieve unique ID, used later as a token for GraphQL queries
        energy_page_response = s.get(
            MYENERGY_PAGE_URL,
            allow_redirects=True,
            params={'accounts': str(account_number)})
        energy_page_response.raise_for_status()

        doc_tree = html.fromstring(energy_page_response.text)
        (unique_id, ) = doc_tree.xpath('//input[@id="uniqueId"]/@value')

        # We will need the session cookies later too
        session_cookies = s.cookies

    return login_page_response, session_cookies, unique_id


def get_graphql_client(login_response, session_cookies, graphql_token):
    """Create a client for GraphQL queries.

    Args:
        login_response (requests.Response): The HTTP response from the login
            page (required to retrieve the session cookies)
        session_cookies (requests.CookieJar): Session cookies, initialised
            at login
        graphql_token (int): The "UniqeID" value retrieve from the login page.
            Used by the "Authorization" header during GraphQL queries.
    """
    # We transform the CookieJar object into a cookies header string
    # The current RequestsHTTPTransport constructor does not support
    # a cookies paramater, so we create a cookie header string instead.
    cookie_header = requests.cookies.get_cookie_header(
        session_cookies,
        login_response)

    headers = {
        'Host': 'www.britishgas.co.uk',
        'Accept': 'application/json, text/plain, */*',
        'Cookie': cookie_header,
        'Authorization': graphql_token,
    }

    return Client(
        transport=RequestsHTTPTransport(
            url=MYENERGY_GRAPHQL_URL,
            headers=headers,
            timeout=TIMEOUT_S),
        fetch_schema_from_transport=True)
