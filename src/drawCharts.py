import os
import pandas as pd
import altair as alt
import streamlit as st
import plotly.express as px
from dataFetch import (INCOME_SEREIS_ID, COMBINED_GAS_AND_UTIL, UTILITY_SEREIES_ID, HEALTH_SERIES_ID,
    GAS_SERIES_ID, GROCERIES_SERIES_ID, TRAVEL_SERIES_ID)

# Set Master Pallette for charts categories
MASTER_PALETTE = {
    'Income': '#4A90E2',
    'Housing': '#F5A623',
    'Utilities': '#7ED321',
    'Health Care': '#9013FE',
    'Gas': '#E67E22',
    'Groceries': '#D0021B',
    'Vacation': '#00A896',
    'Left Over Income': '#4A90E2'
}

# Title mappinig for tool tips
TITLE_NAME_HOVER = {
    'Personal Income': 'Income',
    'Housing': 'Housing',
    'Personal consumption expenditures: Utilities': 'Utilities',
    'Personal consumption expenditures: Services: Health care': 'Health Care',
    'Personal consumption expenditures: Gas Fuel': 'Gas',
    'Personal consumption expenditures: Food': 'Groceries',
    'Personal consumption expenditures: Foreign travel by U.S. residents': 'Vacation',
    'Left Over Income': 'Left Over Income'
    }

def draw_donut_chart(df):

    # group df
    grouped = df.groupby('title')['converted_value'].sum().reset_index()

    # calculate left over income
    inc_val = grouped[grouped['title'] == 'Personal Income']['converted_value'].sum()
    exp_val = grouped[grouped['title'] != 'Personal Income']['converted_value'].sum()
    left_over = inc_val - exp_val

    # Remove personal Inocme
    donut_df = grouped[grouped['title'] != 'Personal Income'].copy()

    # add to donut df if posiitve
    if left_over > 0:
            left_df = pd.DataFrame([{'title': 'Left Over Income', 'converted_value': left_over}])
            donut_df = pd.concat([donut_df, left_df], ignore_index=True)

    # create donut df
    donut_df = donut_df.rename(columns={'title': 'Category', 'converted_value': 'Amount'})
    # Convert title
    donut_df['Category'] = donut_df['Category'].apply(lambda x: TITLE_NAME_HOVER[x])

    # Build plotly
    fig = px.pie(
        donut_df,
        values='Amount',
        names='Category',
        hole=0.70,
        color='Category',
        color_discrete_map=MASTER_PALETTE
    )

    fig.update_layout(
            showlegend=False,
            margin=dict(t=20, b=40, l=30, r=30),
            height=350,
            title_text="Income Distribution",
            title_xanchor='left',
            title_yanchor='top',
            annotations=[
                        {
                            "text": f"Total Breakdown<br><b>${donut_df['Amount'].sum() :.1f}B</b>",
                            "x": 0.5,
                            "y": 0.5,
                            "font_size": 20,
                            "showarrow": False,
                            "align": "center"
                        }]
        )

    fig.update_traces(
        hovertemplate="<b>%{label}</b><br><br>" +
                      "$ %{value:.1f} B<br>" +
                      "<extra></extra>"
    )

    st.plotly_chart(fig, use_container_width=True)

def draw_ticker_card(label, pct_change, absolute_val_str):
    """Generates a styled financial terminal widget for YoY metrics."""
    if pct_change >= 0:
        color = "#00CC96"       # Emerald green
        bg_color = "#0E2F26"    # Forest green sheen
        arrow = "▲"
        sign = "+"
    else:
        color = "#FF3E3E"       # Crimson red
        bg_color = "#351212"    # Maroon sheen
        arrow = "▼"
        sign = ""               # Handled natively by negative numbers

    ticker_html = f"""
    <div style="
        background-color: #111217;
        border: 1px solid #262730;
        border-radius: 8px;
        padding: 15px;
        text-align: left;
        font-family: sans-serif;">
        <div style="font-size: 12px; color: #808495; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">
            {label}
        </div>
        <div style="display: flex; align-items: baseline; gap: 10px;">
            <span style="font-size: 24px; font-weight: 700; color: #FFFFFF;">{absolute_val_str}</span>
            <span style="
                background-color: {bg_color};
                color: {color};
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 14px;
                font-weight: 600;
                display: inline-flex;
                align-items: center;
                gap: 3px;">
                {arrow} {sign}{pct_change:.1%}
            </span>
        </div>
    </div>
    """
    return st.html(ticker_html)

def draw_bar_chart(df):

    chart_df = df[~df['series'].isin([INCOME_SEREIS_ID])].rename(columns={'converted_value': 'Amount'}).copy()

    chart_df['Month'] = pd.to_datetime(chart_df['date']).dt.month_name()
    chart_df['Month_num'] = pd.to_datetime(chart_df['date']).dt.month

    grouped = chart_df.groupby(['Month_num', 'Month', 'title'])['Amount'].sum().reset_index()
    grouped = grouped.sort_values('Month_num')

    month_order = grouped['Month'].unique().tolist()
    # Convert title
    grouped['Category'] = grouped['title'].apply(lambda x: TITLE_NAME_HOVER[x])

    chart = alt.Chart(grouped).mark_bar().encode(
        x=alt.X('Amount:Q', title='Amount ($ Billions)'),
        y=alt.Y('Month:N', title=None, sort=month_order),
        color=alt.Color('Category:N', legend=None,
            scale=alt.Scale(
                            domain=list(MASTER_PALETTE.keys()),
                            range=list(MASTER_PALETTE.values())
                        )),
        tooltip=[
                alt.Tooltip('Category:N', title='title'),
                alt.Tooltip('Amount:Q', title='Amount ($ Billions)', format='.1f')
            ]
    ).properties(
        title="Monthly Spend Breakdown"
    )
    st.altair_chart(chart, use_container_width=True)

def draw_ToT_line_chart(df, pill_filter):

    pills = {
        'Income': INCOME_SEREIS_ID,
        'Housing': 'HOUSING',
        'Utilities': UTILITY_SEREIES_ID,
        'Health Care': HEALTH_SERIES_ID,
        'Gas': GAS_SERIES_ID,
        'Groceries': GROCERIES_SERIES_ID,
        'Vaction': TRAVEL_SERIES_ID
        }

    selected_pills = [pills[p] for p in pill_filter if p in pills.keys()]
    selected_pills.append('PI') # Always add income back for line hraph

    chart_df = df.rename(columns={'pct_change': 'MoM Rate'}).copy()
    chart_df = chart_df[chart_df.series.isin(selected_pills)]
    chart_df = chart_df[chart_df['MoM Rate'].notna()]

    # Convert title
    chart_df['Category'] = chart_df['title'].apply(lambda x: TITLE_NAME_HOVER[x])

    chart = alt.Chart(chart_df).mark_line().encode(
        x=alt.X('date', title=None),
        y=alt.Y('MoM Rate:Q', axis=alt.Axis(format='%')),
        color=alt.Color('Category', legend=None,
            scale=alt.Scale(
                            domain=list(MASTER_PALETTE.keys()),
                            range=list(MASTER_PALETTE.values())
                        )),
        tooltip=[
                alt.Tooltip('Category:N', title='title'),
                alt.Tooltip('MoM Rate:Q', title='Rate', format='.1%')
            ],
        # Reduce Opacity
        opacity=alt.condition(
                "datum.Category == 'Income'",
                alt.value(1.0),
                alt.value(0.30))
    ).properties(title="Monthly Inflation Rate")

    st.altair_chart(chart, use_container_width=True)
