import os
import requests
import numpy as np
import pandas as pd
import configparser
import streamlit as st
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

# Load config file
config = configparser.ConfigParser()
config_path = os.path.join(os.path.dirname(__file__), "config.ini")
config.read(os.path.abspath(config_path))

API_KEY = st.secrets["API_KEY"]

INCOME_SEREIS_ID = 'PI'
COMBINED_GAS_AND_UTIL = 'DNRGRC1M027SBEA'
UTILITY_SEREIES_ID = 'UTILITIES'
HEALTH_SERIES_ID = 'DHLCRC1Q027SBEA'
GAS_SERIES_ID = 'FEULGAS'
GROCERIES_SERIES_ID = 'DFXARC1M027SBEA' # OLD: MRTSSM4451USN, NEW:DFXARC1M027SBEA
TRAVEL_SERIES_ID = 'DFTRRC1A027NBEA'

# De-annualied SAAR Values
SERIES_SCALING_FACTORS = {
    INCOME_SEREIS_ID: (1 / 12) * 0.875,
    'PCES': 1 / 12,
    COMBINED_GAS_AND_UTIL: 1 / 12,
    HEALTH_SERIES_ID: 1 / 12,
    GROCERIES_SERIES_ID: 1 / 12,
    TRAVEL_SERIES_ID: 1
}

def get_conversion_rate (meta_df, unit_col='units'):

    unit = meta_df[unit_col].loc[0]

    if 'billion' in unit.lower():
        convert_rate = 1
    elif 'million' in unit.lower():
        convert_rate = .001
    elif 'trillion' in unit.lower():
        convert_rate = 1000
    else:
        return np.nan

    return convert_rate

@st.cache_data(ttl=86400)
def get_request (end_point, end_point_id, observation_start=None, observation_end=None):

    # Handle data inputs
    realtime_start = date.today().strftime("%Y-%m-%d")
    realtime_end = date.today().strftime("%Y-%m-%d")
    observation_start = date(observation_start, 1, 1).strftime("%Y-%m-%d") if observation_start else date(date.today().year - 30, 1,1)
    observation_end = date(observation_end, 12, 31).strftime("%Y-%m-%d") if observation_end else date(date.today().year - 1, 12, 31)

    # Get meta data from endpoint
    base_url = f"https://api.stlouisfed.org/fred/{end_point}"
    meta_params = {
        f"{end_point}_id": end_point_id,
        "api_key": API_KEY,
        "realtime_start": realtime_start,
        "realtime_end": realtime_end,
        "file_type": "json"
    }
    meta_response = requests.get(base_url, params=meta_params)

    if meta_response.ok:
        meta_data = meta_response.json()
        meta_data = meta_data.get(end_point+"s", [])

        # Get observations data points
        observation_params = {
            f"{end_point}_id": end_point_id,
            "api_key": API_KEY,
            "observation_start": observation_start,
            "observation_end": observation_end,
            "realtime_start": realtime_start,
            "realtime_end": realtime_end,
            "file_type": "json"
        }
        observation_response = requests.get(base_url+'/observations', params=observation_params)

        if observation_response.ok:
            observation_data = observation_response.json()
            observation_data = observation_data.get("observations", [])

            meta_df = pd.DataFrame(meta_data)
            observation_df = pd.DataFrame(observation_data)

            # Clean dfs
            meta_df['series'] = end_point_id
            observation_df['series'] = end_point_id
            observation_df = observation_df.merge(meta_df[['series', "title"]], on='series', how='left')

            # Convert spend amount to $B
            con_rate = get_conversion_rate(meta_df)
            observation_df['value'] = pd.to_numeric(observation_df['value'], errors='coerce')
            observation_df['converted_value'] = (observation_df['value'] * con_rate
                                                if 'Dollars' in meta_df['units'].loc[0]
                                                else observation_df['value'])

            # Some series needs to be scaled and de-annualized from
            scale_factor = SERIES_SCALING_FACTORS.get(end_point_id, 1.0)
            observation_df['converted_value'] = observation_df['converted_value'] * scale_factor

            # Compute change rate and add date related fields
            observation_df['pct_change'] = observation_df['converted_value'].pct_change()
            observation_df['date'] = pd.to_datetime(observation_df['date']).dt.date
            observation_df['year'] = pd.to_datetime(observation_df['date']).dt.year
            observation_df['quarter'] = pd.to_datetime(observation_df['date']).dt.quarter
            observation_df = observation_df.sort_values('date')

            # Format dataframe
            observation_df = observation_df[['title', 'series', 'date', 'year', 'quarter', 'value', 'converted_value', 'pct_change']]
            # Fill any NaN values with yearly average
            observation_df['converted_value'] = observation_df['converted_value'].fillna(observation_df.groupby('year')['converted_value'].transform('mean'))

            return meta_df, observation_df

def get_single_year_metrics (df):

    # summation
    income = df[df['series'] == INCOME_SEREIS_ID]['converted_value'].sum()
    housing = df[df['series'] == 'HOUSING']['converted_value'].sum()
    util = df[df['series'] == UTILITY_SEREIES_ID]['converted_value'].sum()
    health = df[df['series'] == HEALTH_SERIES_ID]['converted_value'].sum()
    gas = df[df['series'] == GAS_SERIES_ID]['converted_value'].sum()
    groceries = df[df['series'] == GROCERIES_SERIES_ID]['converted_value'].sum()
    raw_travel = df[df['series'] == TRAVEL_SERIES_ID]['converted_value'].sum()
    travel_yoy_change = df[df['series'] == TRAVEL_SERIES_ID]['pct_change'].iloc[0] * 100

    # Compute metrics
    neccessities_pct = ((housing + util + health + gas + groceries) / income) * 100
    left_over_income = income - (housing + util + health + gas + groceries)
    post_necessities_pct = (left_over_income / income) * 100
    income_to_necessities_ratio = income / (housing + util + health + gas + groceries)
    total_months = df[df['series'] == INCOME_SEREIS_ID]['date'].nunique() or 12  #df['date'].nunique() or 12 <-- Remove this account for annual travel data
    travel = (raw_travel / 12) * total_months
    avg_health_spend = health / total_months
    avg_gas_spend = gas / total_months
    travel_left_over_pct = travel / left_over_income if left_over_income > 0 else 0

    metrics = {
        "neccessities_pct": neccessities_pct,
        "left_over_income": left_over_income,
        "post_necessities_pct": post_necessities_pct,
        "income_to_necessities_ratio": income_to_necessities_ratio,
        "average_monthly_health_spend": avg_health_spend,
        "average_monthly_gas_spend": avg_gas_spend,
        "travel_to_left_over_pct": travel_left_over_pct,
        "travel_yoy_change": travel_yoy_change
    }

    return metrics

def get_multi_year_metrics (df):

    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date')

    # Calculate growth
    income_spend_avg_growth = df[df['series'] == INCOME_SEREIS_ID]['converted_value'].resample('YE').sum().pct_change().mean() * 100
    housing_spend_avg_growth = df[df['series'] == "HOUSING"]['converted_value'].resample('YE').sum().pct_change().mean() * 100
    util_spend_avg_growth = df[df['series'] == UTILITY_SEREIES_ID]['converted_value'].resample('YE').sum().pct_change().mean() * 100
    health_spend_avg_growth = df[df['series'] == HEALTH_SERIES_ID]['converted_value'].resample('YE').sum().pct_change().mean() * 100
    gas_spend_avg_growth = df[df['series'] == GAS_SERIES_ID]['converted_value'].resample('YE').sum().pct_change().mean() * 100
    grocery_spend_avg_growth = df[df['series'] == GROCERIES_SERIES_ID]['converted_value'].resample('YE').sum().pct_change().mean() * 100
    travel_spend_spend_avg_growth = df[df['series'] == TRAVEL_SERIES_ID]['converted_value'].resample('YE').sum().pct_change().mean() * 100

    # Calculate Average
    income_spend_avg = df[df['series'] == INCOME_SEREIS_ID]['converted_value'].mean()
    housing_spend_avg = df[df['series'] == "HOUSING"]['converted_value'].mean()
    util_spend_avg = df[df['series'] == UTILITY_SEREIES_ID]['converted_value'].mean()
    health_spend_avg = df[df['series'] == HEALTH_SERIES_ID]['converted_value'].mean()
    gas_spend_avg = df[df['series'] == GAS_SERIES_ID]['converted_value'].mean()
    grocery_spend_avg = df[df['series'] == GROCERIES_SERIES_ID]['converted_value'].mean()
    travel_spend_spend_avg = df[df['series'] == TRAVEL_SERIES_ID]['converted_value'].mean()

    metrics = {
        'income_spend_avg_growth': income_spend_avg_growth,
        'housing_spend_avg_growth': housing_spend_avg_growth,
        'util_spend_avg_growth': util_spend_avg_growth,
        'health_spend_avg_growth': health_spend_avg_growth,
        'gas_spend_avg_growth': gas_spend_avg_growth,
        'grocery_spend_avg_growth': grocery_spend_avg_growth,
        'travel_spend_spend_avg_growth': travel_spend_spend_avg_growth,
        'income_spend_avg': income_spend_avg,
        'housing_spend_avg': housing_spend_avg,
        'util_spend_avg': util_spend_avg,
        'health_spend_avg': health_spend_avg,
        'gas_spend_avg': gas_spend_avg,
        'grocery_spend_avg': grocery_spend_avg,
        'travel_spend_spend_avg': travel_spend_spend_avg
    }

    return metrics


@st.cache_data
def collect_single_year_data():
    # Data collection
    pincome_meta_df, pincome_observation_df = get_request('series', INCOME_SEREIS_ID)
    groceries_meta_df, groceries_observation_df = get_request('series', GROCERIES_SERIES_ID)

    # Vacation adjustment
    travel_meta_df, travel_observation_df = get_request('series', TRAVEL_SERIES_ID)
    # Get extensions for new df
    travel_observation_df['date'] = pd.to_datetime(travel_observation_df['date'])
    ext_travel = travel_observation_df.iloc[-1:].copy()[['title', 'series', 'date', 'year', 'quarter']]
    ext_travel['date'] = (ext_travel['date'].iloc[0] +  relativedelta(years=1))
    ext_travel['year'] = ext_travel['date'].dt.year
    ext_travel['quarter'] = ext_travel['date'].dt.quarter
    ext_travel['value'] = np.nan
    travel_observation_df = pd.concat([travel_observation_df, ext_travel])
    # Complete vacation df
    vacation_observation_df = travel_observation_df.set_index('date').resample('MS').ffill()
    vacation_observation_df['converted_value'] = vacation_observation_df['converted_value'] / 12 # de annualize, leave this step to keep pct consitent in utils
    vacation_observation_df = vacation_observation_df.reset_index()
    vacation_observation_df = vacation_observation_df[:-1].copy()
    vacation_observation_df['date'] = vacation_observation_df['date'].dt.date
    vacation_observation_df['year'] = pd.to_datetime(vacation_observation_df['date']).dt.year
    vacation_observation_df['quarter'] = pd.to_datetime(vacation_observation_df['date']).dt.quarter
    vacation_observation_df['series'] = TRAVEL_SERIES_ID
    vacation_observation_df['title'] = 'Personal consumption expenditures: Foreign travel by U.S. residents'

    # Gas & Utilities adjustment
    combined_gas_util_meta, combined_gas_util_df = get_request('series', COMBINED_GAS_AND_UTIL)
    gas_index_meta, gas_index_df = get_request('series', 'CUSR0000SETB01')
    util_index_meta, util_index_df = get_request('series', 'CPIENGSL')

    split_grid = (combined_gas_util_df[['date', 'year', 'quarter', 'converted_value']]
                  .rename(columns={'converted_value': 'total_pce_dollars'})
                  .merge(gas_index_df[['date', 'converted_value']].rename(columns={'converted_value': 'gas_idx'}), on='date', how='left')
                  .merge(util_index_df[['date', 'converted_value']].rename(columns={'converted_value': 'util_idx'}), on='date', how='left'))

    # Apply the Weighting Formula
    split_grid['total_idx_pool'] = split_grid['gas_idx'] + split_grid['util_idx']
    split_grid['gas_weight'] = split_grid['gas_idx'] / split_grid['total_idx_pool']
    split_grid['util_weight'] = split_grid['util_idx'] / split_grid['total_idx_pool']
    split_grid['converted_value_gas'] = split_grid['total_pce_dollars'] * split_grid['gas_weight']
    split_grid['converted_value_util'] = split_grid['total_pce_dollars'] * split_grid['util_weight']
    gas_observation_df = split_grid[['date', 'year', 'quarter', 'converted_value_gas']].rename(columns={'converted_value_gas': 'converted_value'})
    util_observation_df = split_grid[['date', 'year', 'quarter', 'converted_value_util']].rename(columns={'converted_value_util': 'converted_value'})
    gas_observation_df['pct_change'] = gas_observation_df['converted_value'].pct_change()
    util_observation_df['pct_change'] = util_observation_df['converted_value'].pct_change()

    # Assign series and title
    gas_meta_df = combined_gas_util_meta.copy()
    util_meta_df = combined_gas_util_meta.copy()
    gas_observation_df['series'] = 'FEULGAS'
    util_observation_df['series'] = 'UTILITIES'
    gas_observation_df['title'] = "Personal consumption expenditures: Gas Fuel"
    util_observation_df['title'] = "Personal consumption expenditures: Utilities"
    gas_meta_df['series'] = 'FEULGAS'
    util_meta_df['series'] = 'UTILITIES'
    gas_meta_df['title'] = "Personal consumption expenditures: Gas Fuel"
    util_meta_df['title'] = "Personal consumption expenditures: Utilities"

    # Health care specific adjustment
    health_meta_df, health_quarterly_df = get_request('series', HEALTH_SERIES_ID)
    health_quarterly_df['date'] = pd.to_datetime(health_quarterly_df['date'])
    ext_quarter_health = health_quarterly_df.iloc[-1:].copy()[['title', 'series', 'date', 'year', 'quarter']]
    ext_quarter_health['date'] = (ext_quarter_health['date'].iloc[0] +  relativedelta(months=3))
    ext_quarter_health['year'] = ext_quarter_health['date'].dt.year
    ext_quarter_health['quarter'] = ext_quarter_health['date'].dt.quarter
    ext_quarter_health['value'] = np.nan
    health_observation_df = pd.concat([health_quarterly_df, ext_quarter_health])
    # Complete healthcare dt
    health_observation_df = health_observation_df.set_index('date').resample('MS').ffill()[:-1].copy()
    health_observation_df = health_observation_df.reset_index()
    health_observation_df['date'] = pd.to_datetime(health_observation_df['date']).dt.date

    # Housing specific
    total_meta_df, total_observation_df = get_request('series', 'PCES')
    # Hosuing Meta df
    housing_meta_df = total_meta_df
    housing_meta_df['title'] = 'Housing'
    housing_meta_df['series'] = 'HOUSING'
    # Housing observation df
    housing_observation_df = (total_observation_df
                                .merge(util_observation_df[['date', 'converted_value']].rename(columns={'converted_value': 'converted_value_util'}),
                                        on='date', how='left')
                                .merge(health_observation_df[['date', 'converted_value']].rename(columns={'converted_value': 'converted_value_health'}),
                                        on='date', how='left'))
    housing_observation_df['converted_value'] = (housing_observation_df['converted_value'] -
                                                    (housing_observation_df['converted_value_util'].fillna(0) +
                                                    housing_observation_df['converted_value_health'].fillna(0)))
    housing_observation_df['title'] = 'Housing'
    housing_observation_df['series'] = 'HOUSING'

    housing_observation_df = housing_observation_df.sort_values('date')
    housing_observation_df['pct_change'] = housing_observation_df['converted_value'].pct_change()
    housing_observation_df = housing_observation_df[['title', 'series', 'date', 'year', 'quarter', 'converted_value']]
    housing_observation_df['pct_change'] = housing_observation_df['converted_value'].pct_change()

    # Combine all data frames
    default_df = pd.concat([pincome_observation_df, housing_observation_df, util_observation_df, health_observation_df,
                            gas_observation_df, groceries_observation_df, vacation_observation_df]).reset_index()
    default_df = default_df[default_df['series'].isin([INCOME_SEREIS_ID, 'HOUSING', UTILITY_SEREIES_ID, HEALTH_SERIES_ID,
                                                       GAS_SERIES_ID, GROCERIES_SERIES_ID, TRAVEL_SERIES_ID])].copy()

    return default_df
