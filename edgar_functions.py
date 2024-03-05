import os
import pandas as pd
import numpy as np  
import requests
from bs4 import BeautifulSoup
import logging  
import calendar 
import re
from fuzzywuzzy import fuzz
import xml.etree.ElementTree as et

headers = {'user-agent':"usr@example.com"}


pd.options.display.float_format = (
    lambda x: "{:,.0f}".format(x) if int(x) == x else "{:,.2f}".format(x)
)


# Function to extract the first element from a string representation of a list
def extract_first_element(input_string):
    # Regex pattern to find content between single quotes
    pattern = r"'([^']*)'"
    match = re.search(pattern, input_string)
    if match:
        # Return the first matched group (element)
        return match.group(1)
    else:
        # Return None if no match is found
        return None

statement_keys_map = {
    "balance_sheet": [
        "balance sheet",
        "balance sheets",
        "statement of financial position",
        "consolidated balance sheets",
        "consolidated balance sheet",
        "consolidated financial position",
        "consolidated balance sheets - southern",
        "consolidated statements of financial position",
        "consolidated statement of financial position",
        "consolidated statements of financial condition",
        "combined and consolidated balance sheet",
        "condensed consolidated balance sheets",
        "consolidated balance sheets, as of december 31",
        "dow consolidated balance sheets",
        "consolidated balance sheets (unaudited)",
    ],
    "income_statement": [
        "income statement",
        "income statements",
        "statement of earnings (loss)",
        "statements of consolidated income",
        "consolidated statements of operations",
        "consolidated statement of operations",
        "consolidated statements of earnings",
        "consolidated statement of earnings",
        "consolidated statements of income",
        "consolidated statement of income",
        "consolidated income statements",
        "consolidated income statement",
        "condensed consolidated statements of earnings",
        "consolidated results of operations",
        "consolidated statements of income (loss)",
        "consolidated statements of income - southern",
        "consolidated statements of operations and comprehensive income",
        "consolidated statements of comprehensive income",
    ],
    "cash_flow_statement": [
        "cash flows statement",
        "cash flows statements",
        "statement of cash flows",
        "statements of consolidated cash flows",
        "consolidated statements of cash flows",
        "consolidated statement of cash flows",
        "consolidated statement of cash flow",
        "consolidated cash flows statements",
        "consolidated cash flow statements",
        "condensed consolidated statements of cash flows",
        "consolidated statements of cash flows (unaudited)",
        "consolidated statements of cash flows - southern",
    ],
}


def cik_matching_ticker(ticker, headers=headers, fill = True):
    ticker = ticker.upper().replace(".", "-")
    ticker_json = requests.get(
        "https://www.sec.gov/files/company_tickers.json", headers=headers
    ).json()

    for company in ticker_json.values():
        if company["ticker"] == ticker:
            cik = str(company["cik_str"])
            if fill:
                cik = cik.zfill(10)
                return cik
            else:
                return cik           
    raise ValueError(f"Ticker {ticker} not found in SEC database")

def get_same_sic_companies(df, cik=320193, n_accessions=3, n_companies=3):
    tickers = []
    sic = df[df['cik'] == cik].sic.values[0]
    ref_ticker = df[df['cik'] == cik].tickers.values[0]
    ref_ticker = extract_first_element(ref_ticker)

    sic_df = df[df['sic'] == sic]
    for name, ticker in sic_df[['name', 'tickers']].values:
        t = extract_first_element(ticker)
        if t is not None and t != ref_ticker:
            try:
                accession_numbers = get_filtered_filings(t, just_accession_numbers=True, ten_k=True)
                if len(accession_numbers) > n_accessions:
                    c = cik_matching_ticker(t, headers, fill=True)
                    name = df[df['cik'] == int(c)]['name']
                    if len(name) != 0:
                        name = name.values[0]
                    else:
                        name = ""
                    tickers.append((t, c, name))
            except ValueError as e:
                continue

    if len(tickers) < n_companies:
        return tickers
    else:
        return tickers[:n_companies]


def get_submission_data_for_ticker(ticker, headers=headers, only_filings_df=False):
    """
    Get the data in json form for a given ticker. For example: 'cik', 'entityType', 'sic', 'sicDescription', 'insiderTransactionForOwnerExists', 'insiderTransactionForIssuerExists', 'name', 'tickers', 'exchanges', 'ein', 'description', 'website', 'investorWebsite', 'category', 'fiscalYearEnd', 'stateOfIncorporation', 'stateOfIncorporationDescription', 'addresses', 'phone', 'flags', 'formerNames', 'filings'

    Args:
        ticker (str): The ticker symbol of the company.

    Returns:
        json: The submissions for the company.
    """
    cik = cik_matching_ticker(ticker)
    headers = headers
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    company_json = requests.get(url, headers=headers).json()
    if only_filings_df:
        return pd.DataFrame(company_json["filings"]["recent"])
    else:
        return company_json


def get_filtered_filings(
    ticker, ten_k=True, just_accession_numbers=False, headers=headers
):
    """
    Retrieves either 10-K or 10-Q filings for a given ticker and optionally returns just accession numbers.

    Args:
        ticker (str): Stock ticker symbol.
        ten_k (bool): If True, fetches 10-K filings; otherwise, fetches 10-Q filings.
        just_accession_numbers (bool): If True, returns only accession numbers; otherwise, returns full data.
        headers (dict): Headers for HTTP request.

    Returns:
        DataFrame or Series: DataFrame of filings or Series of accession numbers.
    """
    # Fetch submission data for the given ticker
    company_filings_df = get_submission_data_for_ticker(
        ticker, only_filings_df=True, headers=headers)
    # Filter for 10-K or 10-Q forms
    df = company_filings_df[company_filings_df["form"] == ("10-K" if ten_k else "10-Q")]
    # Return accession numbers if specified
    if just_accession_numbers:
        df = df.set_index("reportDate")
        accession_df = df["accessionNumber"]
        return accession_df
    else:
        return df


def get_facts(ticker, headers=headers):
    """
    Retrieves company facts for a given ticker.

    Args:
        ticker (str): Stock ticker symbol.
        headers (dict): Headers for HTTP request.

    Returns:
        dict: Company facts in JSON format.
    """
    # Get CIK number matching the ticker
    cik = cik_matching_ticker(ticker)
    # Construct URL for company facts
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    # Fetch and return company facts
    company_facts = requests.get(url, headers=headers).json()
    return company_facts


def facts_DF(ticker, headers=headers):
    """
    Converts company facts into a DataFrame.

    Args:
        ticker (str): Stock ticker symbol.
        headers (dict): Headers for HTTP request.

    Returns:
        tuple: DataFrame of facts and a dictionary of labels.
    """
    # Retrieve facts data
    facts = get_facts(ticker, headers)
    us_gaap_data = facts["facts"]["us-gaap"]
    df_data = []

    # Process each fact and its details
    for fact, details in us_gaap_data.items():
        for unit in details["units"]:
            for item in details["units"][unit]:
                row = item.copy()
                row["fact"] = fact
                df_data.append(row)

    df = pd.DataFrame(df_data)
    # Convert 'end' and 'start' to datetime
    df["end"] = pd.to_datetime(df["end"])
    df["start"] = pd.to_datetime(df["start"])
    # Drop duplicates and set index
    df = df.drop_duplicates(subset=["fact", "end", "val"])
    df.set_index("end", inplace=True)
    # Create a dictionary of labels for facts
    labels_dict = {fact: details["label"] for fact, details in us_gaap_data.items()}
    return df, labels_dict

def best_label_score_tags(actual_label, list_of_labels_used):
    scores= []
    for labels in list_of_labels_used:
        score1 = fuzz.token_sort_ratio(actual_label, labels)
        score2 = fuzz.WRatio(actual_label, labels)
        score = (score1 + score2)/2
        scores.append(score)
    return max(scores)

def max_value_key(tags_dictionary):
    # Check if the dictionary is empty
    if not tags_dictionary:
        return None
    
    # Find the key with the maximum value
    max_key = max(tags_dictionary, key=tags_dictionary.get)
    
    # Check if the max value is less than 60
    if tags_dictionary[max_key] < 60:
        return "No tags"
    
    return max_key

def assign_tags(score_dictionary):
    assigned_tags ={}
    for label, tags_dictionary in score_dictionary.items():
        assigned_tags[label] = {}
        assigned_tags[label]["company_fact"] = max_value_key(tags_dictionary)
        assigned_tags[label]["format"] = "us-gaap"
    return assigned_tags


def best_label_score_tags(actual_label, list_of_labels_used):
    scores = []
    for labels in list_of_labels_used:
        score1 = fuzz.token_sort_ratio(actual_label, labels)
        score2 = fuzz.WRatio(actual_label, labels)
        score3 = fuzz.token_set_ratio(actual_label, labels)
        score = (score1 + score2 + score3) / 3
        scores.append(score)
    return max(scores)


def max_value_key(tags_dictionary):
    # Check if the dictionary is empty
    if not tags_dictionary:
        return None

    # Find the key with the maximum value
    max_key = max(tags_dictionary, key=tags_dictionary.get)

    # Check if the max value is less than 60
    if tags_dictionary[max_key] < 60:
        return "No tags"

    return max_key


def assign_tags(score_dictionary):
    assigned_tags = {}
    for label, tags_dictionary in score_dictionary.items():
        assigned_tags[label] = {}
        assigned_tags[label]["company_fact"] = max_value_key(tags_dictionary)
        assigned_tags[label]["format"] = "us-gaap"
    return assigned_tags


def get_label_calc_tags(ticker):
    company_labels_to_assign = {"AssetsCurrent": ["Inventories",
                                                  "Accounts Receivables net"],
                                "Assets": ["Total current assets",
                                           "Property and equipment, net"],
                                "LiabilitiesCurrent": ["Accounts payable",
                                                       "Current portion of long-term debt"],
                                "Liabilities": ["Total current liabilities",
                                                "Noncurrent Long-term debt, excluding current portion"],
                                # 'LiabilitiesAndStockholdersEquity' : ["Total current liabilities",
                                #                "Long-term debt, excluding current portion"],
                                "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest": [
                                    "interest expenses"],
                                }

    main_facts = company_labels_to_assign.keys()

    url_lab = ""
    url_cal = ""
    url_xsd = ""
    cik = str(int(cik_matching_ticker(ticker)))
    accession_numbers = get_filtered_filings(ticker, just_accession_numbers=True)
    accession_number = accession_numbers.iloc[0]
    accession_number_with_nodash = accession_number.replace("-", "")
    int_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_number_with_nodash}/{accession_number}-index.html"
    int_content = requests.get(int_url, headers=headers).content
    int_soup = BeautifulSoup(int_content, 'xml')
    int_table = int_soup.find('table', summary="Data Files")
    for link in int_table.find_all('a'):
        if link.text.endswith('_lab.xml'):
            url_lab = link.get("href")
        if link.text.endswith('_cal.xml'):
            url_cal = link.get("href")
        if link.text.endswith(".xsd"):
            url_xsd = link.get("href")
    if url_lab == "":
        url_lab = url_xsd
    if url_cal == "":
        url_cal = url_xsd

    # ---------- Label Tags ------------
    lab_url = f"https://sec.gov{url_lab}"
    lab_content = requests.get(lab_url, headers=headers).content
    lab_soup = BeautifulSoup(lab_content, 'xml')
    label_tags = lab_soup.find_all('link:label')
    label_tags.extend(lab_soup.find_all('label'))

    lab_tags = {}
    lab_pattern = re.compile(r'us-gaap_(.*?)(?:_.*?)?$')
    for tag in label_tags:
        id = tag.get('xlink:label')
        match = lab_pattern.search(id)
        label = tag.text
        if match:
            if match.group(1) in lab_tags.keys():
                lab_tags[match.group(1)].append(label)
            else:
                lab_tags[match.group(1)] = [label]

    # ---------- Calc Tags ------------
    calc_url = f"https://sec.gov{url_cal}"
    calc_content = requests.get(calc_url, headers=headers).content
    calc_soup = BeautifulSoup(calc_content, 'xml')

    calculation_arcs = calc_soup.find_all('link:calculationArc')
    calculation_arcs.extend(calc_soup.find_all('calculationArc'))
    calc_pattern = re.compile(r'us-gaap_(.*?)(?:_.*?)?$')

    cal_tags = {}
    # Iterate through each calculation arc
    for arc in calculation_arcs:
        # Get the 'xlink:to' and 'xlink:from' attributes
        to_attribute = arc.get('xlink:to')
        from_attribute = arc.get('xlink:from')
        match_to = calc_pattern.search(to_attribute)
        match_from = calc_pattern.search(from_attribute)

        # Check if both attributes start with 'loc_us-gaap_'
        if match_to and match_from:
            # Extract the main fact and subsidiary fact using regular expressions
            main_fact = match_from.group(1)
            under_fact = match_to.group(1)

            if main_fact in cal_tags.keys():
                # If it is, append the subsidiary fact to the list of values
                cal_tags[main_fact].append(under_fact)
            else:
                # If not, create a new entry with the main fact as key and a list containing the subsidiary fact as value
                cal_tags[main_fact] = [under_fact]

    # Initialize an empty dictionary to hold the hierarchy
    fact_label_hierarchy = {}

    # Iterate through each reference_main_fact in the filtered main_facts set
    for reference_main_fact in main_facts:
        # Initialize a nested dictionary for each reference_main_fact
        fact_label_hierarchy[reference_main_fact] = {}
        if reference_main_fact not in cal_tags.keys():
            for key in cal_tags.keys():
                if reference_main_fact in cal_tags[key]:
                    mf = key
                    break
        else:
            mf = reference_main_fact
        for tag_name in cal_tags[mf]:
            fact_label_hierarchy[reference_main_fact][tag_name] = lab_tags[tag_name]

    scores = {}
    for main_fact in main_facts:
        for actual_label in company_labels_to_assign[main_fact]:
            scores[actual_label] = {}
            for tag, list_of_labels in fact_label_hierarchy[main_fact].items():
                score = best_label_score_tags(actual_label, list_of_labels)
                scores[actual_label][tag] = score

    assigned_tags = assign_tags(scores)

    order = ["Inventories",
             "Accounts Receivables net",
             "Total current assets",
             "Property and equipment, net",
             "Accounts payable",
             "Current portion of long-term debt",
             "Total current liabilities",
             "Long-term debt, excluding current portion",
             "Total current liabilities",
             "Long-term debt, excluding current portion",
             "interest expenses"]

    # Custom sorting function
    sorted_dict = {key: assigned_tags[key] for key in order if key in assigned_tags}
    return {"assigned_tags": sorted_dict, "scores": scores, "cal_tags": cal_tags, "lab_tags": lab_tags,
            "fact_label_hierarchy": fact_label_hierarchy}


def annual_facts(ticker, headers=headers):
    """
    Fetches and processes annual (10-K) financial facts for a given ticker.

    Args:
        ticker (str): Stock ticker symbol.
        headers (dict): Headers for HTTP request.

    Returns:
        DataFrame: Transposed pivot table of annual financial facts.
    """
    # Get accession numbers for 10-K filings
    accession_nums = get_filtered_filings(
        ticker, ten_k=True, just_accession_numbers=True, headers=headers
    )
    # Extract and process facts data
    df, label_dict = facts_DF(ticker, headers)
    # Filter data for 10-K filings
    ten_k = df[df["accn"].isin(accession_nums)]
    ten_k = ten_k[ten_k.index.isin(accession_nums.index)]
    # Pivot and format the data
    pivot = ten_k.pivot_table(values="val", columns="fact", index="end")
    pivot.rename(columns=label_dict, inplace=True)
    return pivot.T


def quarterly_facts(ticker, headers=headers):
    """
    Fetches and processes quarterly (10-Q) financial facts for a given ticker.

    Args:
        ticker (str): Stock ticker symbol.
        headers (dict): Headers for HTTP request.

    Returns:
        DataFrame: Transposed pivot table of quarterly financial facts.
    """
    # Get accession numbers for 10-Q filings
    accession_nums = get_filtered_filings(
        ticker, ten_k=False, just_accession_numbers=True, headers=headers
    )
    # Extract and process facts data
    df, label_dict = facts_DF(ticker, headers)
    # Filter data for 10-Q filings
    ten_q = df[df["accn"].isin(accession_nums)]
    ten_q = ten_q[ten_q.index.isin(accession_nums.index)].reset_index(drop=False)
    # Remove duplicate entries
    ten_q = ten_q.drop_duplicates(subset=["fact", "end"], keep="last")
    # Pivot and format the data
    pivot = ten_q.pivot_table(values="val", columns="fact", index="end")
    pivot.rename(columns=label_dict, inplace=True)
    return pivot.T

def generate_main_df(fys, selected_tickers):
    main_df = pd.DataFrame()
    for ticker in selected_tickers:
        company_facts = {
            "Total assets": {"company_fact": "Assets", "format": "us-gaap"},
            "Total liabilities": {"company_fact": "Liabilities", "format": "us-gaap"},
            "Retained earnings": {"company_fact": "RetainedEarningsAccumulatedDeficit", "format": "us-gaap"},
            "Operating Income": {"company_fact": "OperatingIncomeLoss", "format": "us-gaap"},
            "Total stockholders' equity": {
                "company_fact": ["StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
                                 "StockholdersEquity"], "format": "us-gaap"},
            "Net income attributable to the shareholders": {"company_fact": "NetIncomeLoss", "format": "us-gaap"},
            "Net income per share": {"company_fact": "EarningsPerShareBasic", "format": "us-gaap"},
            "Dividend per share": {"company_fact": "CommonStockDividendsPerShareDeclared", "format": "us-gaap"},
            "number of share outstanding": {"company_fact": "CommonStockSharesOutstanding", "format": "us-gaap"}
        }
        cik = cik_matching_ticker(ticker)
        response = requests.get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json", headers=headers)
        data = response.json()['facts']
        company_facts_update = get_label_calc_tags(ticker)['assigned_tags']
        company_facts.update(company_facts_update)
        company_df = pd.DataFrame()
        for fact_name, tag_details in company_facts.items():
            tag = tag_details['company_fact']
            format = tag_details['format']
            list_of_tags = data[format].keys()
            values = []
            tag_in_taglist = False
            if type(tag) == type([]):
                for t in tag:
                    if t in list_of_tags:
                        tag_in_taglist = True
                        tag = t
                        break;
            if type(tag) == type(""):
                if tag in list_of_tags:
                    tag_in_taglist = True
            if tag_in_taglist:
                key = list(data[format][tag]['units'].keys())[0]
                for fy in fys:
                    available = False
                    for info in data[format][tag]['units'][key]:
                        if info['fy'] == fy and info['form'] == '10-K':
                            available = True
                            val = info['val']
                    if available is False:
                        val = 'N/A'
                    values.append(val)
            else:
                values = ["N/A"] * len(fys)

            temp = pd.DataFrame({"FY": fys, "Value": values})
            temp['Fact'] = fact_name
            if len(company_df) == 0:
                company_df = temp
            else:
                company_df = pd.concat([company_df, temp])
        company_df['Ticker'] = ticker
        company_df = company_df[['Ticker', 'Fact', 'Value', 'FY']]
        if len(main_df) == 0:
            main_df = company_df
        else:
            main_df = pd.concat([main_df, company_df])

    return main_df


def save_dataframe_to_csv(dataframe, folder_name, ticker, statement_name, frequency):
    """
    Saves a given DataFrame to a CSV file in a specified directory.

    Args:
        dataframe (DataFrame): The DataFrame to be saved.
        folder_name (str): The folder name where the CSV file will be saved.
        ticker (str): Stock ticker symbol.
        statement_name (str): Name of the financial statement.
        frequency (str): Frequency of the financial data (e.g., annual, quarterly).

    Returns:
        None
    """
    # Create directory path
    directory_path = os.path.join(folder_name, ticker)
    os.makedirs(directory_path, exist_ok=True)
    # Construct file path and save DataFrame
    file_path = os.path.join(directory_path, f"{statement_name}_{frequency}.csv")
    dataframe.to_csv(file_path)


def _get_file_name(report):
    """
    Extracts the file name from an XML report tag.

    Args:
        report (Tag): BeautifulSoup tag representing the report.

    Returns:
        str: File name extracted from the tag.
    """
    html_file_name_tag = report.find("HtmlFileName")
    xml_file_name_tag = report.find("XmlFileName")
    # Return the appropriate file name
    if html_file_name_tag:
        return html_file_name_tag.text
    elif xml_file_name_tag:
        return xml_file_name_tag.text
    else:
        return ""


def _is_statement_file(short_name_tag, long_name_tag, file_name):
    """
    Determines if a given file is a financial statement file.

    Args:
        short_name_tag (Tag): BeautifulSoup tag for the short name.
        long_name_tag (Tag): BeautifulSoup tag for the long name.
        file_name (str): Name of the file.

    Returns:
        bool: True if it's a statement file, False otherwise.
    """
    return (
        short_name_tag is not None
        and long_name_tag is not None
        and file_name  # Ensure file_name is not an empty string
        and "Statement" in long_name_tag.text
    )


def get_statement_file_names_in_filing_summary(ticker, accession_number, headers=headers):
    """
    Retrieves file names of financial statements from a filing summary.

    Args:
        ticker (str): Stock ticker symbol.
        accession_number (str): SEC filing accession number.
        headers (dict): Headers for HTTP request.

    Returns:
        dict: Dictionary mapping statement types to their file names.
    """
    try:
        # Set up request session and get filing summary
        session = requests.Session()
        cik = cik_matching_ticker(ticker)
        base_link = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_number}"
        filing_summary_link = f"{base_link}/FilingSummary.xml"
        filing_summary_response = session.get(
            filing_summary_link, headers=headers
        ).content.decode("utf-8")

        # Parse the filing summary
        filing_summary_soup = BeautifulSoup(filing_summary_response, "lxml-xml")
        statement_file_names_dict = {}
        # Extract file names for statements
        for report in filing_summary_soup.find_all("Report"):
            file_name = _get_file_name(report)
            short_name, long_name = report.find("ShortName"), report.find("LongName")
            if _is_statement_file(short_name, long_name, file_name):
                statement_file_names_dict[short_name.text.lower()] = file_name
        return statement_file_names_dict
    except requests.RequestException as e:
        print(f"An error occurred: {e}")
        return {}


def get_statement_soup(
    ticker, accession_number, statement_name, headers, statement_keys_map
):
    """
    Retrieves the BeautifulSoup object for a specific financial statement.

    Args:
        ticker (str): Stock ticker symbol.
        accession_number (str): SEC filing accession number.
        statement_name (str): has to be 'balance_sheet', 'income_statement', 'cash_flow_statement'
        headers (dict): Headers for HTTP request.
        statement_keys_map (dict): Mapping of statement names to keys.

    Returns:
        BeautifulSoup: Parsed HTML/XML content of the financial statement.

    Raises:
        ValueError: If the statement file name is not found or if there is an error fetching the statement.
    """
    session = requests.Session()
    cik = cik_matching_ticker(ticker)
    base_link = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_number}"
    # Get statement file names
    statement_file_name_dict = get_statement_file_names_in_filing_summary(
        ticker, accession_number, headers
    )
    statement_link = None
    # Find the specific statement link
    for possible_key in statement_keys_map.get(statement_name.lower(), []):
        file_name = statement_file_name_dict.get(possible_key.lower())
        if file_name:
            statement_link = f"{base_link}/{file_name}"
            break
    if not statement_link:
        raise ValueError(f"Could not find statement file name for {statement_name}")
    # Fetch the statement
    try:
        statement_response = session.get(statement_link, headers=headers)
        statement_response.raise_for_status()  # Check for a successful request
        # Parse and return the content
        if statement_link.endswith(".xml"):
            return BeautifulSoup(
                statement_response.content, "lxml-xml", from_encoding="utf-8"
            )
        else:
            return BeautifulSoup(statement_response.content, "lxml")
    except requests.RequestException as e:
        raise ValueError(f"Error fetching the statement: {e}")


def extract_columns_values_and_dates_from_statement(soup):
    """
    Extracts columns, values, and dates from an HTML soup object representing a financial statement.

    Args:
        soup (BeautifulSoup): The BeautifulSoup object of the HTML document.

    Returns:
        tuple: Tuple containing columns, values_set, and date_time_index.
    """
    columns = []
    values_set = []
    date_time_index = get_datetime_index_dates_from_statement(soup)

    for table in soup.find_all("table"):
        unit_multiplier = 1
        special_case = False

        # Check table headers for unit multipliers and special cases
        table_header = table.find("th")
        if table_header:
            header_text = table_header.get_text()
            # Determine unit multiplier based on header text
            if "in Thousands" in header_text:
                unit_multiplier = 1
            elif "in Millions" in header_text:
                unit_multiplier = 1000
            # Check for special case scenario
            if "unless otherwise specified" in header_text:
                special_case = True

        # Process each row of the table
        for row in table.select("tr"):
            onclick_elements = row.select("td.pl a, td.pl.custom a")
            if not onclick_elements:
                continue

            # Extract column title from 'onclick' attribute
            onclick_attr = onclick_elements[0]["onclick"]
            column_title = onclick_attr.split("defref_")[-1].split("',")[0]
            columns.append(column_title)

            # Initialize values array with NaNs
            values = [np.NaN] * len(date_time_index)

            # Process each cell in the row
            for i, cell in enumerate(row.select("td.text, td.nump, td.num")):
                if "text" in cell.get("class"):
                    continue

                # Clean and parse cell value
                value = keep_numbers_and_decimals_only_in_string(
                    cell.text.replace("$", "")
                    .replace(",", "")
                    .replace("(", "")
                    .replace(")", "")
                    .strip()
                )
                if value:
                    value = float(value)
                    # Adjust value based on special case and cell class
                    if special_case:
                        value /= 1000
                    else:
                        if "nump" in cell.get("class"):
                            values[i] = value * unit_multiplier
                        else:
                            values[i] = -value * unit_multiplier

            values_set.append(values)

    return columns, values_set, date_time_index


def get_datetime_index_dates_from_statement(soup: BeautifulSoup) -> pd.DatetimeIndex:
    """
    Extracts datetime index dates from the HTML soup object of a financial statement.

    Args:
        soup (BeautifulSoup): The BeautifulSoup object of the HTML document.

    Returns:
        pd.DatetimeIndex: A Pandas DatetimeIndex object containing the extracted dates.
    """
    table_headers = soup.find_all("th", {"class": "th"})
    dates = [str(th.div.string) for th in table_headers if th.div and th.div.string]
    dates = [standardize_date(date).replace(".", "") for date in dates]
    index_dates = pd.to_datetime(dates)
    return index_dates


def standardize_date(date: str) -> str:
    """
    Standardizes date strings by replacing abbreviations with full month names.

    Args:
        date (str): The date string to be standardized.

    Returns:
        str: The standardized date string.
    """
    for abbr, full in zip(calendar.month_abbr[1:], calendar.month_name[1:]):
        date = date.replace(abbr, full)
    return date


def keep_numbers_and_decimals_only_in_string(mixed_string: str):
    """
    Filters a string to keep only numbers and decimal points.

    Args:
        mixed_string (str): The string containing mixed characters.

    Returns:
        str: String containing only numbers and decimal points.
    """
    num = "1234567890."
    allowed = list(filter(lambda x: x in num, mixed_string))
    return "".join(allowed)


def create_dataframe_of_statement_values_columns_dates(
    values_set, columns, index_dates
) -> pd.DataFrame:
    """
    Creates a DataFrame from statement values, columns, and index dates.

    Args:
        values_set (list): List of values for each column.
        columns (list): List of column names.
        index_dates (pd.DatetimeIndex): DatetimeIndex for the DataFrame index.

    Returns:
        pd.DataFrame: DataFrame constructed from the given data.
    """
    transposed_values_set = list(zip(*values_set))
    df = pd.DataFrame(transposed_values_set, columns=columns, index=index_dates)
    return df


def process_one_statement(ticker, accession_number, statement_name):
    """
    Processes a single financial statement identified by ticker, accession number, and statement name.

    Args:
        ticker (str): The stock ticker.
        accession_number (str): The SEC accession number.
        statement_name (str): Name of the financial statement.

    Returns:
        pd.DataFrame or None: DataFrame of the processed statement or None if an error occurs.
    """
    try:
        # Fetch the statement HTML soup
        soup = get_statement_soup(
            ticker,
            accession_number,
            statement_name,
            headers=headers,
            statement_keys_map=statement_keys_map,
        )
    except Exception as e:
        logging.error(
            f"Failed to get statement soup: {e} for accession number: {accession_number}"
        )
        return None

    if soup:
        try:
            # Extract data and create DataFrame
            columns, values, dates = extract_columns_values_and_dates_from_statement(
                soup
            )
            df = create_dataframe_of_statement_values_columns_dates(
                values, columns, dates
            )

            if not df.empty:
                # Remove duplicate columns
                df = df.T.drop_duplicates()
            else:
                logging.warning(
                    f"Empty DataFrame for accession number: {accession_number}"
                )
                return None

            return df
        except Exception as e:
            logging.error(f"Error processing statement: {e}")
            return None

