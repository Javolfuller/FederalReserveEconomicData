import sys
import os
sys.path.append(os.path.abspath("src"))
import numpy as np
import pandas as pd
import streamlit as st
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from src.dataFetch import get_request, get_single_year_metrics, get_multi_year_metrics, collect_single_year_data
from src.drawCharts import (draw_donut_chart, draw_ticker_card, draw_bar_chart_yearly, draw_bar_chart_monthly,
                            draw_spend_total_spend_over_time, draw_ToT_line_chart, draw_category_spend_trend)

# Set canvas layout
st.set_page_config(
    page_title="FRED Economic Discovery Analysis",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Capture current session state
active_year = st.session_state.get('year_choice', (date.today().year - 1))
active_view = st.session_state.get('view_choice', 'Monthly:')

# Data collection
default_df = collect_single_year_data()

###################################
######### Build Dashboard #########
###################################

# Set side bar
st.sidebar.title("Federal Resever Economic Discovery Analysis")
st.markdown(
    """
    <style>
        [data-testid="stSidebar"] {
            width: 200px !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.write("Filters")

    # Year Filter
    view = st.radio("Select a View", ["Monthly:", "Yearly:"], key='view_choice')
    if view == 'Monthly:':
        year_options = default_df.year[default_df.year.notna()].astype(int).sort_values(ascending=False).unique()
        active_year = st.selectbox("Select Year", year_options, key='year_choice')
        year_start = active_year if active_year else date.today().year - 1
        year_end = active_year if active_year else date.today().year - 1
    else:
        year_start, year_end = st.slider("Select Time Frame",
            min_value=default_df['year'].min(),
            max_value=default_df['year'].max(),
            value=(default_df['year'].min(), default_df['year'].max()),
            step=1)

# Filter data set & get related metrics
year_filter = default_df.year.between(year_start, year_end)
chart_df = default_df[year_filter].copy()
metrics = get_single_year_metrics(chart_df) if view == 'Monthly:' else get_multi_year_metrics(chart_df)

col1, col2, col3 = st.columns(3)
col4, col5, col6 = st.columns(3)

with col1:
    with st.container(border=True):
        if view == 'Monthly:':
            st.metric(label='Necessity Usage', value=f"{metrics['neccessities_pct']:.0f}%")
        else:
            draw_ticker_card(
                    time_frame='Year',
                    label="Average Housing Spend Growth",
                    pct_change=metrics['housing_spend_avg_growth'],
                    absolute_val_str=metrics['housing_spend_avg_growth']
                )

with col2:
    with st.container(border=True):
        if view == 'Monthly:':
            st.metric(label='Left Over Income Percentage', value=f"{metrics['post_necessities_pct']:.0f}%")
        else:
            draw_ticker_card(
                    time_frame='Year',
                    label="Average Utility Spend Growth",
                    pct_change=metrics['util_spend_avg_growth'],
                    absolute_val_str=metrics['util_spend_avg']
                )

with col3:
    with st.container(border=True):
        if view == 'Monthly:':
            st.metric(label='Income to Necessities Ratio', value=f"{metrics['income_to_necessities_ratio']:.2f}")
        else:
            draw_ticker_card(
                    time_frame='Year',
                    label="Average Health-Care Spend Growth",
                    pct_change=metrics['health_spend_avg_growth'],
                    absolute_val_str=metrics['health_spend_avg']
                )

with col4:
    with st.container(border=True):
        if view == 'Monthly:':
            st.metric(label='Monthly Average Health Spend', value=f"${metrics['average_monthly_health_spend']:.2f} B")
        else:
            draw_ticker_card(
                    time_frame='Year',
                    label="Average Feul Spend Growth",
                    pct_change=metrics['gas_spend_avg_growth'],
                    absolute_val_str=metrics['gas_spend_avg']
                )

with col5:
    with st.container(border=True):
        if view == 'Monthly:':
            st.metric(label='Monthly Average gas Spend', value=f"${metrics['average_monthly_gas_spend']:.2f} B")
        else:
            draw_ticker_card(
                    time_frame='Year',
                    label="Average Grocery Spend Growth",
                    pct_change=metrics['grocery_spend_avg_growth'],
                    absolute_val_str=metrics['grocery_spend_avg']
                )

with col6:
    with st.container(border=True):
        if view == 'Monthly:':
            st.metric(label='Foreign Travel Spend Growth', value=f"{metrics['travel_yoy_change']:.0f}%")
        else:
            draw_ticker_card(
                    time_frame='Year',
                    label="Average Foreign Travel Spend Growth",
                    pct_change=metrics['travel_spend_spend_avg_growth'],
                    absolute_val_str=metrics['travel_spend_spend_avg']
                )


# Charts
col7, col8 = st.columns(2, border=True)

with col7:
    if view == 'Monthly:':
        draw_donut_chart(chart_df)
    elif view == 'Yearly:':
        draw_spend_total_spend_over_time(chart_df)

with col8:
    if view == 'Monthly:':
        draw_bar_chart_monthly(chart_df)
    elif view == 'Yearly:':
        draw_bar_chart_yearly(chart_df)

with st.container(border=True):

    # Set categories
    categories = ['Income', 'Housing', 'Utilities', 'Health Care', 'Gas', 'Groceries', 'Vaction']

    # Apply filter and set chart
    active_filters = st.session_state.get('pill_choice', categories)

    if view == 'Monthly:':
        draw_ToT_line_chart(chart_df, active_filters)
    elif view == 'Yearly:':
        draw_category_spend_trend(chart_df, active_filters)

    left_pad, pill_col, right_pad = st.columns([2,5,2])

    with pill_col:
        # Show filter sleection
        pill_selection = st.pills(
            label='Filter by Category',
            options=['Housing', 'Utilities', 'Health Care', 'Gas', 'Groceries', 'Vaction'],
            default=['Housing', 'Utilities', 'Health Care', 'Gas', 'Groceries','Vaction'],
            selection_mode='multi',
            label_visibility='collapsed',
            key='pill_choice')
