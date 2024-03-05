from edgar_functions import *
import pandas as pd


companies_data = [
    {"Company": "Hershey Co.", "Ticker": "HSY", "Cik": "0000047111"},
    {"Company": "Walmart", "Ticker": "WMT", "Cik": "0000104169"},
    {"Company": "Paccar", "Ticker": "PCAR", "Cik": "0000075362"},
    {"Company": "Sysco Corp.", "Ticker": "SYY", "Cik": "0000096021"},
    {"Company": "Tesla", "Ticker": "TSLA", "Cik": "0001318605"},
    {"Company": "General Motors", "Ticker": "GM", "Cik": "0001467858"},
    {"Company": "Target Corp", "Ticker": "TGT", "Cik": "0000027419"},
    {"Company": "Kraft Inc.", "Ticker": "KHC", "Cik": "0001637459"},
    {"Company": "The Clorox Company", "Ticker": "CLX", "Cik": "0000021076"},
    {"Company": "Amazon Inc.", "Ticker": "AMZN", "Cik": "0001018724"},
    {"Company": "Nike Inc.", "Ticker": "NKE", "Cik": "0000320187"},
    {"Company": "Chipotle Mexican Grill Inc.", "Ticker": "CMG", "Cik": "0001058090"},
    {"Company": "McDonald's Inc", "Ticker": "MCD", "Cik": "0000063908"},
    {"Company": "Lululemon Athletics Inc. (LULU)", "Ticker": "LULU", "Cik": "0001397187"},
    {"Company": "Coca Cola", "Ticker": "KO", "Cik": "0000021344"},
    {"Company": "Molson Coors", "Ticker": "TAP", "Cik": "0000024545"}
]
df = pd.read_csv("Final_company_data.csv")
ticker = "WMT"
cik = cik_matching_ticker(ticker)
int_cik = int(cik)

similar_companies = get_same_sic_companies(df, cik = int_cik)

selected_tickers = [x[0] for x in similar_companies]
selected_tickers.append(ticker)

print(selected_tickers)

fys = [2023,2022,2021,2020]
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

print(main_df)



