import os
import pandas as pd
import altair as alt
import streamlit as st
import plotly.express as px
from streamlit_echarts import st_echarts
from dataFetch import (INCOME_SEREIS_ID, COMBINED_GAS_AND_UTIL, UTILITY_SEREIES_ID, HEALTH_SERIES_ID,
    GAS_SERIES_ID, GROCERIES_SERIES_ID, TRAVEL_SERIES_ID)

MASTER_PALETTE = {
    'Income': '#115f9a',         # Deep Corporate Blue
    'Housing': '#1984c5',        # Slate Blue
    'Utilities': '#22a7f0',      # Electric Sky Blue
    'Health Care': '#ff8a5c',    # Soft Coral/Salmon (The circuit breaker for crossing lines!)
    'Gas': '#48b5c4',            # Crisp Deep Teal
    'Groceries': '#76c68f',      # Sage Green
    'Vacation': '#a6d75b',       # Bright Lime Green
    'Left Over Income': '#115f9a'
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
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='#ffffff',
            title_text="Income Distribution",
            title_xanchor='left',
            title_yanchor='top',
            annotations=[
                        {
                            "text": f"Total Breakdown<br><b>${inc_val:.2f} B</b>",
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

def draw_ticker_card(time_frame, prefix_val_format, postfix_val_format, label, sub_label, absolute_val_str, pct_change):
    # 1. Handle background colors and icons for the trend badge
        badge_html = ""
        if pct_change is not None:
            if pct_change >= 0:
                text_color = "#1E7E34"
                bg_color = "#E6F4EA"
                icon = "↑"
                sign = "+"
            else:
                text_color = "#D93025"       # Deep crisp red text
                bg_color = "#FCE8E6"         # Soft light red pill background
                icon = "↓"
                sign = ""                    # Negative sign is automatically provided

            badge_html = f"""
            <div style="display: inline-flex; align-items: center; justify-content: center; margin-top: 10px;">
                <span style="
                    background-color: {bg_color};
                    color: {text_color};
                    padding: 4px 10px;
                    border-radius: 20px;
                    font-size: 13px;
                    font-weight: 600;
                    display: flex;
                    align-items: center;
                    gap: 4px;
                    line-height: 1;">
                    <span>{icon}</span> <span>{sign}{pct_change:.2f}%</span>
                </span>
            </div>
            <div>
                <span style="color: #525866; font-size: 14px;">{sub_label}</span>
            </div>
            """
        else:
            badge_html = '<div style="height: 23px; margin-top: 6px;"></div>'

        # 2. Complete structural card wrapper
        card_html = f"""
        <div style="
            background-color: #161b22;
            padding: 20px;
            text-align: center;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            box-shadow: 0 1px 3px rgba(0,0,0,0.2);
            min-height: 140px;
            display: flex;
            height: 165px;
            box-sizing: border-box;
            flex-direction: column;
            justify-content: center;">

            <div style="font-size: 13px; color: #808495; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; font-weight: 500;">
                {label} <span style="color: #525866; font-size: 11px;">({time_frame})</span>
            </div>

            <div style="font-size: 28px; font-weight: 700; color: #FFFFFF; line-height: 1.2;">
               {prefix_val_format} {absolute_val_str} {postfix_val_format}
            </div>

            {badge_html}
        </div>
        """
        return st.html(card_html)


def draw_spend_total_spend_over_time (df):

    essential_df = df[df.series.isin([INCOME_SEREIS_ID, TRAVEL_SERIES_ID])].copy()
    income_df = df[df['series'] == INCOME_SEREIS_ID].copy()

    grouped_ess_df = essential_df.groupby('year')['converted_value'].sum().reset_index()
    grouped_inc_df = income_df.groupby('year')['converted_value'].sum().reset_index()
    grouped_ess_df['Category'] = 'Necessities'
    grouped_inc_df['Category'] = 'Income'
    chart_df = pd.concat([grouped_ess_df, grouped_inc_df])
    chart_df = chart_df.rename(columns={'converted_value': 'Amount'})

    # Draw Chart
    chart = alt.Chart(chart_df).mark_line(point=False).encode(
        x=alt.X('year', title='Year', axis=alt.Axis(format='d')),
        y=alt.Y('Amount:Q', title='Amount ($ Billions)', axis=alt.Axis(format='.2f')),
        color=alt.Color('Category:N',
            legend=alt.Legend(
                            title=None,
                            orient='bottom',
                            direction='horizontal'),
            scale=alt.Scale(
                            domain=list(['Necessities', 'Income']),
                            range=list(['#D0021B', '#4A90E2'])
                        )),
        tooltip=[
                alt.Tooltip('year:O', title='Year'),
                alt.Tooltip('Amount:Q', title='Total Spend', format='$.2f')
            ]).properties(title="Total Essential Spend Trend")

    st.altair_chart(chart, use_container_width=True)


def draw_bar_chart_monthly(df):

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
        title="Monthly Spend Breakdown",
        width='container',
        height=400
    )
    st.altair_chart(chart, use_container_width=True)


def draw_bar_chart_yearly(df):

    chart_df = df[~df['series'].isin([INCOME_SEREIS_ID])].rename(columns={'converted_value': 'Amount'}).copy()
    grouped = chart_df.groupby(['year', 'title'])['Amount'].sum().reset_index()
    # year_order = grouped['year'].sort_values().unique().tolist()

    # Convert title
    grouped['Category'] = grouped['title'].apply(lambda x: TITLE_NAME_HOVER[x])

    chart = alt.Chart(grouped).mark_bar().encode(
        x=alt.X('Amount:Q', title='Amount ($ Billions)'),
        y=alt.Y('year:O', title='Year'),
        color=alt.Color('Category:N', legend=None,
            scale=alt.Scale(
                            domain=list(MASTER_PALETTE.keys()),
                            range=list(MASTER_PALETTE.values())
                        )),
        tooltip=[
                alt.Tooltip('Category:N', title='title'),
                alt.Tooltip('year:O', title='Year', format='d'),
                alt.Tooltip('Amount:Q', title='Amount ($ Billions)', format='.1f')
            ]
    ).properties(
        title="Yearly Spend Breakdown",
        width='container',
        height=400
    )
    st.altair_chart(chart, use_container_width=True)


# def draw_ToT_line_chart(df, pill_filter):

#     pills = {
#         'Income': INCOME_SEREIS_ID,
#         'Housing': 'HOUSING',
#         'Utilities': UTILITY_SEREIES_ID,
#         'Health Care': HEALTH_SERIES_ID,
#         'Gas': GAS_SERIES_ID,
#         'Groceries': GROCERIES_SERIES_ID,
#         'Vacation': TRAVEL_SERIES_ID
#     }

#     selected_pills = [pills[p] for p in pill_filter if p in pills.keys()]

#     if 'PI' not in selected_pills:
#         selected_pills.append('PI')

#     chart_df = df.rename(columns={'pct_change': 'MoM Rate'}).copy()
#     chart_df = chart_df[chart_df.series.isin(selected_pills)]
#     chart_df = chart_df[chart_df['MoM Rate'].notna()]

#     chart_df['Category'] = chart_df['title'].apply(lambda x: TITLE_NAME_HOVER[x])
#     chart_df = chart_df.sort_values('date')

#     x_data = chart_df['date'].dt.strftime('%b %d').unique().tolist()

#     active_categories = chart_df['Category'].unique().tolist()

#     fallback_colors = ['#115f9a', '#1984c5', '#22a7f0', '#48b5c4', '#76c68f', '#a6d75b', '#d8f3dc']
#     chart_colors = [MASTER_PALETTE.get(cat, fallback_colors[i % len(fallback_colors)]) for i, cat in enumerate(active_categories)]

#     series_list = []
#     for category in active_categories:
#         category_df = chart_df[chart_df['Category'] == category]
#         y_data = (category_df['MoM Rate'] * 100).tolist()

#         line_opacity = 1.0 if category == 'Income' else 0.35
#         area_opacity = 0.08 if category == 'Income' else 0.02

#         series_list.append({
#             "name": category,
#             "type": "line",
#             "smooth": False,
#             "symbol": "circle",
#             "symbolSize": 6,
#             "showSymbol": False,
#             "lineStyle": {
#                 "width": 3 if category == 'Income' else 2,
#                 "opacity": line_opacity
#             },
#             "areaStyle": {
#                 "opacity": area_opacity
#             },
#             "data": y_data
#         })

#     options = {
#         "title": {
#             "text": "Monthly Inflation Rate",
#             "textStyle": {"color": "#FFFFFF", "fontSize": 14, "fontWeight": 600},
#             "left": "0%"
#         },
#         "color": chart_colors,
#         "backgroundColor": "transparent",
#         "tooltip": {
#             "trigger": "axis",

#             "className": "echarts-tooltip-dark",
#             "axisPointer": {
#                 "type": "line",
#                 "lineStyle": {"color": "#525866", "type": "dashed", "width": 1},
#                 "handle": {"show": False}
#             },
#             "backgroundColor": "#161b22",
#             "borderColor": "#21262d",
#             "borderWidth": 1,
#             "textStyle": {"color": "#FFFFFF", "fontFamily": "sans-serif"},
#             "valueFormatter": "{value:.2f}%"
#         },
#         "grid": {
#             "left": "4%",
#             "right": "4%",
#             "bottom": "15%",
#             "containLabel": True
#         },
#         "xAxis": {
#             "type": "category",
#             "boundaryGap": False,
#             "data": x_data,
#             "axisLabel": {"color": "#808495", "fontSize": 11},
#             "axisLine": {"lineStyle": {"color": "#21262d"}},
#             "triggerEvent": True
#         },
#         "yAxis": {
#             "type": "value",
#             "axisLabel": {
#                 "color": "#808495",
#                 "fontSize": 11,
#                 "formatter": "{value}%"
#             },
#             "splitLine": {"lineStyle": {"color": "#21262d", "type": "solid"}},
#             "axisLine": {"show": False}
#         },
#         "series": series_list
#     }

#     return st_echarts(options=options, height="380px")


def draw_ToT_line_chart(df, pill_filter):

    pills = {
        'Income': INCOME_SEREIS_ID,
        'Housing': 'HOUSING',
        'Utilities': UTILITY_SEREIES_ID,
        'Health Care': HEALTH_SERIES_ID,
        'Gas': GAS_SERIES_ID,
        'Groceries': GROCERIES_SERIES_ID,
        'Vacation': TRAVEL_SERIES_ID
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


def draw_category_spend_trend(df, pill_filter):

    pills = {
        'Income': INCOME_SEREIS_ID,
        'Housing': 'HOUSING',
        'Utilities': UTILITY_SEREIES_ID,
        'Health Care': HEALTH_SERIES_ID,
        'Gas': GAS_SERIES_ID,
        'Groceries': GROCERIES_SERIES_ID,
        'Vacation': TRAVEL_SERIES_ID
        }

    selected_pills = [pills[p] for p in pill_filter if p in pills.keys()]
    selected_pills.append('PI') # Always add income back for line hraph

    # calculate yearly YoY change
    grouped = df.groupby(['title', 'series', 'year'])['converted_value'].sum().reset_index()
    grouped = grouped.sort_values(['series', 'year']).reset_index(drop=True)
    grouped['YoY Rate'] = grouped.groupby('series')['converted_value'].pct_change()

    chart_df = grouped[grouped.series.isin(selected_pills)]
    chart_df = chart_df[chart_df['YoY Rate'].notna()]

    # Convert title
    chart_df['Category'] = chart_df['title'].apply(lambda x: TITLE_NAME_HOVER[x])

    chart = alt.Chart(chart_df).mark_line().encode(
        x=alt.X('year', title=None, axis=alt.Axis(format='d')),
        y=alt.Y('YoY Rate:Q', axis=alt.Axis(format='%')),
        color=alt.Color('Category', legend=None,
            scale=alt.Scale(
                            domain=list(MASTER_PALETTE.keys()),
                            range=list(MASTER_PALETTE.values())
                        )),
        tooltip=[
                alt.Tooltip('Category:N', title='title'),
                alt.Tooltip('YoY Rate:Q', title='Rate', format='.1%')
            ],
        # Reduce Opacity
        opacity=alt.condition(
                "datum.Category == 'Income'",
                alt.value(1.0),
                alt.value(0.30))
    ).properties(title="Yearly Inflation Rate")

    st.altair_chart(chart, use_container_width=True)
