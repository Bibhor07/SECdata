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
cik = int("0000047111")
print(get_same_sic_companies(df, cik = cik))




