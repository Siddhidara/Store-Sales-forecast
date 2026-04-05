import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import json, os

st.set_page_config(
    page_title="Store Sales Dashboard",
    page_icon="🛒",
    layout="wide",
)

# ── Styling ───────────────────────────────────────────
st.markdown("""
<style>
/* Light theme */
@media (prefers-color-scheme: light) {
  [data-testid="stAppViewContainer"] { background: #FAFAFA; }
  .kpi {
    background: white;
    border-radius: 12px;
    border: 1px solid #E5E7EB;
    padding: 18px;
    text-align: center;
  }
  .kpi-label { font-size: 12px; color: #6B7280; }
  .kpi-value { font-size: 26px; font-weight: bold; color: #111827; }
  .kpi-good { color: #059669; }
}

/* Dark theme */
@media (prefers-color-scheme: dark) {
  [data-testid="stAppViewContainer"] { background: #0E1117; }
  .kpi {
    background: #1C1F26;
    border-radius: 12px;
    border: 1px solid #30363D;
    padding: 18px;
    text-align: center;
  }
  .kpi-label { font-size: 12px; color: #8B949E; }
  .kpi-value { font-size: 26px; font-weight: bold; color: #E6EDF3; }
  .kpi-good { color: #3FB950; }
}
</style>
""", unsafe_allow_html=True)

DATA = "streamlit_data"

# ── Load Data ─────────────────────────────────────────
@st.cache_data
def load():
    preds = pd.read_csv(f"{DATA}/predictions.csv")
    preds['date'] = pd.to_datetime(preds['date'], errors='coerce')

    stores = pd.read_csv(f"{DATA}/store_summary.csv")
    daily = pd.read_csv(f"{DATA}/daily_trend.csv", parse_dates=['date'])

    with open(f"{DATA}/metrics.json") as f:
        metrics = json.load(f)

    return preds, stores, daily, metrics

preds, stores, daily, metrics = load()

# ── Sidebar ───────────────────────────────────────────
type_map = {
    'a': 'Standard Small',
    'b': 'Large Full-Service',
    'c': 'Medium',
    'd': 'Large Standard'
}

with st.sidebar:
    st.title("🛒 Sales Forecast")

    selected_types = st.multiselect(
        "Store Category",
        options=list(type_map.keys()),
        default=list(type_map.keys()),
        format_func=lambda x: type_map[x]
    )

    filtered_stores = stores[
        stores['store_type'].isin(selected_types)
    ]

    # Only valid stores (with predictions)
    valid_store_ids = preds['store_id'].unique()

    store_list = sorted([
        s for s in filtered_stores['Store'].unique()
        if s in valid_store_ids
    ])

    if not store_list:
        st.error("No stores available")
        st.stop()

    selected_store = st.selectbox("Select Store", store_list)

    st.caption(f"{len(store_list)} stores available")

# ── Header ────────────────────────────────────────────
st.title("🛒 Store Sales Forecast")
st.markdown("Forecast for next 28 days")

# ── Store Data ────────────────────────────────────────
store_row = stores[stores['Store'] == selected_store].iloc[0]

store_preds = preds[
    preds['store_id'] == selected_store
].sort_values('date')

# ── KPI Calculations ──────────────────────────────────
if store_preds.empty:
    avg_actual = 0
    avg_forecast = 0
else:
    avg_actual = store_preds['actual_sales'].mean()
    avg_forecast = store_preds['forecast'].mean()

avg_actual = 0 if np.isnan(avg_actual) else avg_actual
avg_forecast = 0 if np.isnan(avg_forecast) else avg_forecast

pct_diff = (
    (avg_forecast - avg_actual) / avg_actual * 100
    if avg_actual > 0 else 0
)

accuracy = round(100 - abs(pct_diff), 1) if avg_actual > 0 else 0

# ── KPI UI ────────────────────────────────────────────
def kpi(col, label, value):
    col.markdown(f"""
    <div class="kpi">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{value}</div>
    </div>
    """, unsafe_allow_html=True)

k1, k2, k3, k4 = st.columns(4)

kpi(k1, "Store", f"#{selected_store}")
kpi(k2, "Avg Actual", f"€{avg_actual:,.0f}")
kpi(k3, "Forecast", f"€{avg_forecast:,.0f}")
kpi(k4, "Accuracy", f"{accuracy}%")

# ── Forecast Chart ────────────────────────────────────
st.markdown("### 28-Day Forecast")

if store_preds.empty:
    st.warning("No forecast available for this store")
else:
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=store_preds['date'],
        y=store_preds['actual_sales'],
        name='Actual',
        line=dict(color='black')
    ))

    fig.add_trace(go.Scatter(
        x=store_preds['date'],
        y=store_preds['forecast'],
        name='Forecast',
        line=dict(color='#6366F1')
    ))

    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

# ── Overall Trend ─────────────────────────────────────
st.markdown("### Overall Sales Trend")

fig2 = go.Figure()
fig2.add_trace(go.Scatter(
    x=daily['date'],
    y=daily['avg_sales'],
    fill='tozeroy'
))

fig2.update_layout(height=300)
st.plotly_chart(fig2, use_container_width=True)

# ── Sales by Store Category ───────────────────────────
st.markdown("### Sales by Store Category")

cat_data = (
    stores[stores['store_type'].isin(selected_types)]
    .groupby('store_type')['avg_daily_sales']
    .mean()
    .reset_index()
    .sort_values('avg_daily_sales', ascending=False)
)

cat_data['store_type_label'] = cat_data['store_type'].map(type_map)

fig3 = go.Figure(go.Bar(
    x=cat_data['avg_daily_sales'],
    y=cat_data['store_type_label'],
    orientation='h',
    text=cat_data['avg_daily_sales'].apply(lambda v: f'€{v:,.0f}'),
    textposition='outside'
))

fig3.update_layout(height=300)
st.plotly_chart(fig3, use_container_width=True)

# ── Store Table ───────────────────────────────────────
st.markdown("### All Stores Overview")

display = stores[
    stores['store_type'].isin(selected_types)
].copy()

display['store_type'] = display['store_type'].map(type_map)

display = display.rename(columns={
    'Store': 'Store ID',
    'store_type': 'Category',
    'avg_daily_sales': 'Avg Sales (€)'
})

st.dataframe(display, use_container_width=True)

# ── Footer ────────────────────────────────────────────
st.caption(
    f"{metrics['total_stores']} stores | "
    f"{metrics['date_from']} → {metrics['date_to']}"
)
# import streamlit as st
# import pandas as pd
# import numpy as np
# import plotly.graph_objects as go
# import json, os

# st.set_page_config(
#     page_title="Store Sales Dashboard",
#     page_icon="🛒",
#     layout="wide",
# )

# # ── Styling ───────────────────────────────────────────
# st.markdown("""
# <style>
#   [data-testid="stAppViewContainer"] { background: #FAFAFA; }
#   .kpi {
#     background: white;
#     border-radius: 12px;
#     border: 1px solid #E5E7EB;
#     padding: 18px 20px;
#     text-align: center;
#   }
#   .kpi-label {
#     font-size: 12px; color: #6B7280;
#     font-weight: 500; text-transform: uppercase;
#     margin-bottom: 6px;
#   }
#   .kpi-value {
#     font-size: 26px; font-weight: 700; color: #111827;
#   }
#   .kpi-good { color: #059669 !important; }
# </style>
# """, unsafe_allow_html=True)

# DATA = "streamlit_data"

# # ── Load data ─────────────────────────────────────────
# @st.cache_data
# def load():
#     preds = pd.read_csv(f"{DATA}/predictions.csv")
#     preds['date'] = pd.to_datetime(preds['date'], errors='coerce')

#     stores = pd.read_csv(f"{DATA}/store_summary.csv")

#     daily = pd.read_csv(f"{DATA}/daily_trend.csv", parse_dates=['date'])

#     with open(f"{DATA}/metrics.json") as f:
#         metrics = json.load(f)

#     return preds, stores, daily, metrics

# preds, stores, daily, metrics = load()

# # ── Sidebar ───────────────────────────────────────────
# with st.sidebar:
#     st.markdown("## 🛒 Sales Forecast")
#     st.divider()

#     type_map = {
#         'a': 'Standard Small',
#         'b': 'Large Full-Service',
#         'c': 'Medium',
#         'd': 'Large Standard'
#     }

#     type_opts = {
#         type_map.get(t, t): t
#         for t in sorted(stores['store_type'].unique())
#     }

#     selected_types_display = st.multiselect(
#         "Store category",
#         options=list(type_opts.keys()),
#         default=list(type_opts.keys()),
#     )

#     selected_types = [type_opts[t] for t in selected_types_display]

#     filtered_stores = stores[
#         stores['store_type'].isin(selected_types)
#     ]

#     # 🔥 Only stores with predictions
#     valid_store_ids = preds['store_id'].unique()

#     store_list = sorted([
#         s for s in filtered_stores['Store'].unique()
#         if s in valid_store_ids
#     ])

#     if len(store_list) == 0:
#         st.error("No stores available.")
#         st.stop()

#     selected_store = st.selectbox("Select store", store_list)

#     st.caption(f"Showing {len(store_list)} stores with forecasts")

# # ── Header ────────────────────────────────────────────
# st.title("🛒 Store Sales Forecast")
# st.markdown("Next 28 days sales prediction")

# # ── Store Data ────────────────────────────────────────
# store_row_df = stores[stores['Store'] == selected_store]

# if store_row_df.empty:
#     st.warning("No store data available")
#     st.stop()

# store_row = store_row_df.iloc[0]

# store_preds = preds[preds['store_id'] == selected_store] \
#                 .sort_values('date')

# # ── KPI Calculations ──────────────────────────────────
# if store_preds.empty:
#     avg_actual = 0
#     avg_forecast = 0
# else:
#     avg_actual = store_preds['actual_sales'].mean()
#     avg_forecast = store_preds['forecast'].mean()

# avg_actual = 0 if np.isnan(avg_actual) else avg_actual
# avg_forecast = 0 if np.isnan(avg_forecast) else avg_forecast

# pct_diff = (
#     (avg_forecast - avg_actual) / avg_actual * 100
#     if avg_actual > 0 else 0
# )

# accuracy = round(100 - abs(pct_diff), 1) if avg_actual > 0 else 0

# # ── KPI UI ────────────────────────────────────────────
# def kpi(col, label, value):
#     col.markdown(f"""
#     <div class="kpi">
#       <div class="kpi-label">{label}</div>
#       <div class="kpi-value">{value}</div>
#     </div>""", unsafe_allow_html=True)

# k1, k2, k3, k4 = st.columns(4)

# kpi(k1, "Store", f"#{selected_store}")
# kpi(k2, "Avg Actual", f"€{avg_actual:,.0f}")
# kpi(k3, "Forecast", f"€{avg_forecast:,.0f}")
# kpi(k4, "Accuracy", f"{accuracy}%")

# # ── Forecast Chart ────────────────────────────────────
# st.markdown("### 28-Day Forecast")

# if store_preds.empty:
#     st.warning("No forecast available for this store")
# else:
#     fig = go.Figure()

#     fig.add_trace(go.Scatter(
#         x=store_preds['date'],
#         y=store_preds['actual_sales'],
#         name='Actual',
#         line=dict(color='black')
#     ))

#     fig.add_trace(go.Scatter(
#         x=store_preds['date'],
#         y=store_preds['forecast'],
#         name='Forecast',
#         line=dict(color='#6366F1')
#     ))

#     fig.update_layout(height=400)
#     st.plotly_chart(fig, use_container_width=True)

# # ── Trend ─────────────────────────────────────────────
# st.markdown("### Overall Trend")

# fig2 = go.Figure()
# fig2.add_trace(go.Scatter(
#     x=daily['date'],
#     y=daily['avg_sales'],
#     fill='tozeroy'
# ))

# fig2.update_layout(height=300)
# st.plotly_chart(fig2, use_container_width=True)

# # ── Footer ────────────────────────────────────────────
# st.caption(
#     f"{metrics['total_stores']} stores | "
#     f"{metrics['date_from']} → {metrics['date_to']}"
# )
# import streamlit as st
# import pandas as pd
# import numpy as np
# import plotly.graph_objects as go
# import plotly.express as px
# import json, os

# st.set_page_config(
#     page_title = "Store Sales Dashboard",
#     page_icon  = "🛒",
#     layout     = "wide",
# )

# st.markdown("""
# <style>
#   [data-testid="stAppViewContainer"] { background: #FAFAFA; }
#   .kpi {
#     background: white;
#     border-radius: 12px;
#     border: 1px solid #E5E7EB;
#     padding: 18px 20px;
#     text-align: center;
#   }
#   .kpi-label {
#     font-size: 12px; color: #6B7280;
#     font-weight: 500; text-transform: uppercase;
#     letter-spacing: .06em; margin-bottom: 6px;
#   }
#   .kpi-value {
#     font-size: 26px; font-weight: 700; color: #111827;
#   }
#   .kpi-delta {
#     font-size: 12px; color: #6B7280; margin-top: 4px;
#   }
#   .kpi-good { color: #059669 !important; }
# </style>
# """, unsafe_allow_html=True)

# DATA = 'streamlit_data'

# @st.cache_data
# def load():
#     preds  = pd.read_csv(f'{DATA}/predictions.csv')
#     stores = pd.read_csv(f'{DATA}/store_summary.csv')
#     daily  = pd.read_csv(f'{DATA}/daily_trend.csv',
#                          parse_dates=['date'])
#     with open(f'{DATA}/metrics.json') as f:
#         metrics = json.load(f)
#     logs_path = f'{DATA}/training_logs.csv'
#     logs = pd.read_csv(logs_path) \
#            if os.path.exists(logs_path) else None
#     return preds, stores, daily, metrics, logs

# preds, stores, daily, metrics, logs = load()

# # ── Sidebar ───────────────────────────────────────────
# with st.sidebar:
#     st.markdown("## 🛒 Sales Forecast")
#     st.markdown("Forecast the next 28 days of store sales.")
#     st.divider()

#     st.markdown("### Filter Stores")
#     type_map = {
#         'a': 'Standard Small',
#         'b': 'Large Full-Service',
#         'c': 'Medium',
#         'd': 'Large Standard'
#     }
#     type_opts = {
#         type_map.get(t, t): t
#         for t in sorted(stores['store_type'].unique())
#     }
#     selected_types_display = st.multiselect(
#         "Store category",
#         options = list(type_opts.keys()),
#         default = list(type_opts.keys()),
#     )
#     selected_types = [type_opts[t] for t in selected_types_display]

#     filtered_stores = stores[
#         stores['store_type'].isin(selected_types)]
#     valid_store_ids = preds['store_id'].unique()

#     store_list = sorted([
#         s for s in filtered_stores['Store'].unique()
#         if s in valid_store_ids
#     ])
#     if len(store_list) == 0:
#     st.error("No stores available for selected filters.")
#     st.stop()

#     selected_store = st.selectbox(
#         "Select a store",
#         options     = store_list,
#         format_func = lambda s: (
#             f"Store {s} — "
#             f"{type_map.get(stores[stores['Store']==s]['store_type'].values[0], '')}"
#         ),
#     )

#     st.divider()
#     st.markdown("### Display options")
#     show_range = st.checkbox(
#         "Show expected high/low range", value=True)

#     st.divider()
#     st.caption(f"Data: {metrics['date_from']} → {metrics['date_to']}")
#     st.caption(f"Stores: {metrics['total_stores']}")

# # ── Page header ───────────────────────────────────────
# st.title("🛒 Store Sales Forecast")
# st.markdown(
#     "See how sales are expected to perform over the "
#     "next 4 weeks, and explore trends across all stores.")

# # ── KPI row ───────────────────────────────────────────
# store_row_df = stores[stores['Store'] == selected_store]

# if store_row_df.empty:
#     st.warning("No data for this store.")
#     st.stop()

# store_row = store_row_df.iloc[0]
# store_preds = preds[preds['store_id'] == selected_store]

# if store_preds.empty:
#     avg_actual = 0
#     avg_forecast = 0
# else:
#     avg_actual = store_preds['actual_sales'].mean()
#     avg_forecast = store_preds['forecast'].mean()

# # Handle NaN
# avg_actual = 0 if np.isnan(avg_actual) else avg_actual
# avg_forecast = 0 if np.isnan(avg_forecast) else avg_forecast
# pct_diff     = (
#     (avg_forecast - avg_actual) / avg_actual * 100
#     if avg_actual > 0 else 0
# )
# accuracy = round(100 - abs(pct_diff), 1)

# def kpi(col, label, value, delta="", good=False):
#     delta_class = 'kpi-good' if good else ''
#     col.markdown(f"""
#     <div class="kpi">
#       <div class="kpi-label">{label}</div>
#       <div class="kpi-value">{value}</div>
#       <div class="kpi-delta {delta_class}">{delta}</div>
#     </div>""", unsafe_allow_html=True)

# k1, k2, k3, k4 = st.columns(4)

# kpi(k1, "Store",
#     f"#{selected_store}",
#     type_map.get(store_row['store_type'], ''))
# kpi(k2, "Avg actual sales (daily)",
#     f"€{avg_actual:,.0f}",
#     "last 28 days")
# kpi(k3, "Forecasted sales (daily)",
#     f"€{avg_forecast:,.0f}",
#     "next 28 days")
# kpi(k4, "Forecast accuracy",
#     f"{accuracy}%",
#     "vs actual", good=True)

# st.markdown("<br>", unsafe_allow_html=True)

# # ── Forecast chart ────────────────────────────────────
# st.markdown("### 28-Day Sales Forecast")

# if store_preds.empty:
#     st.warning(
#         "No forecast data for this store. "
#         "Try selecting a different store.")
# else:
#     fig = go.Figure()

#     # Confidence band
#     if show_range and 'forecast_high' in store_preds.columns:
#         fig.add_trace(go.Scatter(
#             x = pd.concat([
#                 store_preds['date'],
#                 store_preds['date'].iloc[::-1]
#             ]),
#             y = pd.concat([
#                 store_preds['forecast_high'],
#                 store_preds['forecast_low'].iloc[::-1]
#             ]),
#             fill      = 'toself',
#             fillcolor = 'rgba(99, 102, 241, 0.10)',
#             line      = dict(color='rgba(0,0,0,0)'),
#             name      = 'Expected range',
#             showlegend= True,
#         ))

#     # Actual sales
#     fig.add_trace(go.Scatter(
#         x    = store_preds['date'],
#         y    = store_preds['actual_sales'],
#         name = 'Actual sales',
#         line = dict(color='#111827', width=2),
#         mode = 'lines+markers',
#         marker = dict(size=5),
#     ))

#     # Forecast — single clean line
#     fig.add_trace(go.Scatter(
#         x    = store_preds['date'],
#         y    = store_preds['forecast'],
#         name = 'Forecasted sales',
#         line = dict(color='#6366F1', width=2.5),
#         mode = 'lines',
#     ))

#     fig.update_layout(
#         height      = 420,
#         margin      = dict(l=0, r=0, t=10, b=0),
#         xaxis_title = "Date",
#         yaxis_title = "Daily Sales (€)",
#         plot_bgcolor  = 'white',
#         paper_bgcolor = 'white',
#         legend = dict(orientation='h', y=1.08, x=0),
#         xaxis  = dict(gridcolor='#F3F4F6', tickangle=45),
#         yaxis  = dict(gridcolor='#F3F4F6', tickprefix='€'),
#         hovermode = 'x unified',
#     )
#     st.plotly_chart(fig, use_container_width=True)

#     if show_range:
#         st.caption(
#             "The shaded area shows the expected high and low range. "
#             "Actual sales should fall within this band most of the time.")

# st.divider()

# # ── Two column section ────────────────────────────────
# col_l, col_r = st.columns(2)

# # ── Overall sales trend ───────────────────────────────
# with col_l:
#     st.markdown("### Overall Sales Trend")
#     st.caption("Average daily sales across all stores")

#     fig2 = go.Figure()
#     fig2.add_trace(go.Scatter(
#         x         = daily['date'],
#         y         = daily['avg_sales'],
#         fill      = 'tozeroy',
#         fillcolor = 'rgba(99,102,241,0.08)',
#         line      = dict(color='#6366F1', width=2),
#         name      = 'Avg daily sales',
#     ))
#     fig2.update_layout(
#         height        = 300,
#         margin        = dict(l=0, r=0, t=10, b=0),
#         plot_bgcolor  = 'white',
#         paper_bgcolor = 'white',
#         xaxis         = dict(gridcolor='#F3F4F6', tickangle=45),
#         yaxis         = dict(gridcolor='#F3F4F6', tickprefix='€'),
#         showlegend    = False,
#         hovermode     = 'x',
#     )
#     st.plotly_chart(fig2, use_container_width=True)

# # ── Forecast accuracy breakdown ───────────────────────
# with col_r:
#     st.markdown("### Forecast Accuracy Breakdown")
#     st.caption("How close the forecast was to actual sales")

#     accuracy_data = store_preds.copy()
#     accuracy_data['error_pct'] = (
#         abs(accuracy_data['actual_sales'] -
#             accuracy_data['forecast']) /
#         accuracy_data['actual_sales'].replace(0, np.nan) * 100
#     ).fillna(0).round(1)

#     fig3 = go.Figure(go.Bar(
#         x            = accuracy_data['date'],
#         y            = accuracy_data['error_pct'],
#         marker_color = accuracy_data['error_pct'].apply(
#             lambda v: '#34D399' if v < 10
#                       else '#FBBF24' if v < 20
#                       else '#F87171'
#         ),
#     ))
#     fig3.add_hline(
#         y                = 10,
#         line_dash        = 'dash',
#         line_color       = '#34D399',
#         annotation_text  = 'Good (< 10%)',
#     )
#     fig3.update_layout(
#         height        = 300,
#         margin        = dict(l=0, r=0, t=10, b=0),
#         plot_bgcolor  = 'white',
#         paper_bgcolor = 'white',
#         xaxis         = dict(
#             gridcolor      = '#F3F4F6',
#             tickangle      = 45,
#             showticklabels = False),
#         yaxis         = dict(
#             gridcolor  = '#F3F4F6',
#             ticksuffix = '%',
#             title      = 'Forecast error'),
#         showlegend    = False,
#     )
#     st.plotly_chart(fig3, use_container_width=True)
#     st.caption(
#         "Green = within 10% of actual  |  "
#         "Yellow = within 20%  |  "
#         "Red = more than 20% off")

# st.divider()

# # ── Sales by store category ───────────────────────────
# st.markdown("### Sales by Store Category")
# st.caption("Which store types generate the most daily revenue")

# cat_data = (
#     stores[stores['store_type'].isin(selected_types)]
#     .groupby('store_type')['avg_daily_sales']
#     .mean()
#     .reset_index()
# )
# cat_data['store_type_label'] = cat_data['store_type'].map(type_map)
# cat_data = cat_data.sort_values('avg_daily_sales', ascending=True)

# fig4 = go.Figure(go.Bar(
#     x            = cat_data['avg_daily_sales'],
#     y            = cat_data['store_type_label'],
#     orientation  = 'h',
#     marker_color = '#6366F1',
#     text         = cat_data['avg_daily_sales'].apply(
#                        lambda v: f'€{v:,.0f}'),
#     textposition = 'outside',
# ))
# fig4.update_layout(
#     height        = 260,
#     margin        = dict(l=0, r=60, t=10, b=0),
#     plot_bgcolor  = 'white',
#     paper_bgcolor = 'white',
#     xaxis         = dict(gridcolor='#F3F4F6', tickprefix='€'),
#     yaxis         = dict(gridcolor='white'),
#     showlegend    = False,
# )
# st.plotly_chart(fig4, use_container_width=True)

# st.divider()

# # ── Store overview table ──────────────────────────────
# st.markdown("### All Stores Overview")
# st.caption("Browse and compare all stores")

# display_stores = stores[
#     stores['store_type'].isin(selected_types)].copy()

# display_stores['store_type']  = display_stores['store_type'].map(type_map)
# display_stores['assortment']  = display_stores['assortment'].map(
#     {'a': 'Basic', 'b': 'Extra', 'c': 'Extended'})
# display_stores['competition_m'] = (
#     display_stores['competition_m'].fillna(0).astype(int))

# display_stores = display_stores.rename(columns={
#     'Store'          : 'Store ID',
#     'store_type'     : 'Category',
#     'assortment'     : 'Product Range',
#     'avg_daily_sales': 'Avg Daily Sales (€)',
#     'promo_rate_pct' : 'Promo Days (%)',
#     'competition_m'  : 'Nearest Competitor (m)',
# })

# st.dataframe(
#     display_stores[[
#         'Store ID', 'Category', 'Product Range',
#         'Avg Daily Sales (€)', 'Promo Days (%)',
#         'Nearest Competitor (m)']],
#     use_container_width = True,
#     height              = 320,
#     hide_index          = True,
# )

# # ── Footer ────────────────────────────────────────────
# st.divider()
# st.caption(
#     f"Sales Forecast Dashboard — Rossmann Retail | "
#     f"{metrics['total_stores']} stores | "
#     f"{metrics['date_from']} to {metrics['date_to']}"
# )