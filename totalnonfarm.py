import requests
import pandas as pd
from io import StringIO
from bs4 import BeautifulSoup

def load_total_nonfarm_employment():
    # Set cookies and headers for BLS access
    cookies = {
        '_ga': 'GA1.1.23832994.1754936123',
        'nmstat': 'dd11f381-0922-cc91-6d5f-cf1a4417680c',
        '_ga_CSLL4ZEK4L': 'GS2.1.s1754942514$o2$g1$t1754942618$j42$l0$h0',
    }

    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
        'Referer': 'https://download.bls.gov/pub/time.series/sm/',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
    }

    # Download main data
    url = "https://download.bls.gov/pub/time.series/sm/sm.data.1.AllData"
    response = requests.get(url, headers=headers, cookies=cookies)
    response.raise_for_status()

    df = pd.read_csv(StringIO(response.content.decode('utf-8', errors='replace')), sep="\t")
    df.columns = [col.strip() for col in df.columns]
    df['year'] = pd.to_numeric(df['year'], errors='coerce')

    # Filter rows
    df = df[
        df.iloc[:, 0].str.strip().str.startswith("SMS") &
        df.iloc[:, 0].str.strip().str.endswith("00000000001") &
        (df['year'] < 2010)
    ]

    # Create date column
    df['month'] = df['period'].str.extract(r'M(\d{2})').astype(int)
    df['date'] = pd.to_datetime(dict(year=df['year'], month=df['month'], day=1))

    df = df.drop(columns=['year', 'period', 'month'])

    df = df.drop(df.columns[-2], axis=1)

    # Extract state and area codes
    series_base = df.iloc[:, 0].str.replace(r'^SMS', '', regex=True)
    series_base = series_base.str.replace(r'00000000001$', '', regex=True)
    df['state_fips'] = series_base.str[:2]
    df['area_code'] = series_base.str[2:6].astype(str)

    # Fetch and parse MSA/CSA crosswalk
    crosswalk_url = "https://www.bls.gov/cew/classifications/areas/county-msa-csa-crosswalk.htm"
    response = requests.get(crosswalk_url, headers=headers, cookies=cookies)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table", {"class": "regular"})
    names = pd.read_html(str(table))[0]
    names.columns = [col.strip() for col in names.columns]
    names = names.drop(columns=['County Code', 'County Title'], errors='ignore')
    names['MSA Code'] = names['MSA Code'].str.replace(r'^C', '', regex=True)
    names = names.rename(columns={'MSA Code': 'area_code'})
    names['area_code'] = names['area_code'].astype(str)

    # Merge
    df = df.merge(names, on='area_code', how='left')
    df = df.dropna(subset=['MSA Title', 'CSA Title'], how='any')
    df = df.drop_duplicates(subset=['area_code', 'date'])
    df = df.drop(columns=['series_id'])
    df = df.rename(columns={'value': 'Total NonFarm Employment in 1000s'})
    df['Total NonFarm Employment in 1000s'] = df['Total NonFarm Employment in 1000s'] * 1000

    df = df[[
        'state_fips',
        'area_code',
        'MSA Title',
        'CSA Code',
        'CSA Title',
        'date',
        'Total NonFarm Employment in 1000s'
    ]]

    return df


df = load_total_nonfarm_employment()
df.to_csv("TNFEMP.csv", index=False)
