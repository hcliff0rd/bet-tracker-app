# Bet Tracker Streamlit App
# -------------------------------------------------
# Streamlit web app version of the Bet Tracker prototype.
# Run locally with: streamlit run app.py
# Or deploy free via Streamlit Cloud: https://share.streamlit.io

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

# -------------------------------------------------
# Configuration
STARTING_BANKROLLS = {
    'FanDuel': 200.0,
    'DraftKings': 200.0,
    'Caesars': 200.0,
}
CSV_PATH = 'bets_log.csv'

# -------------------------------------------------
# Helper functions

def american_to_decimal(odds):
    try:
        odds = float(odds)
    except (TypeError, ValueError):
        return np.nan
    if odds > 0:
        return 1 + (odds / 100.0)
    else:
        return 1 + (100.0 / abs(odds))


def load_bets(path=CSV_PATH):
    try:
        df = pd.read_csv(path, parse_dates=['date'])
        return df
    except FileNotFoundError:
        cols = ['date','sport','market','book','bet_type','selection','odds_american','odds_decimal','stake','result','profit','expected_value','closing_line','notes']
        return pd.DataFrame(columns=cols)


def save_bets(df, path=CSV_PATH):
    df.to_csv(path, index=False)


def add_bet(df, bet_data):
    df = pd.concat([df, pd.DataFrame([bet_data])], ignore_index=True)
    save_bets(df)
    return df


def compute_metrics(df):
    df['cumulative_profit'] = df['profit'].cumsum()
    total_staked = df['stake'].sum()
    total_profit = df['profit'].sum()
    roi = (total_profit / total_staked) if total_staked else 0
    win_rate = (df['profit'] > 0).sum() / len(df) if len(df) else 0
    return {
        'Total Bets': len(df),
        'Total Staked': total_staked,
        'Total Profit': total_profit,
        'ROI': roi,
        'Win Rate': win_rate,
    }


def bankroll_simulation(df):
    df = df.sort_values('date')
    running = {b: STARTING_BANKROLLS.get(b, 0.0) for b in df['book'].unique()}
    rows = []
    for _, r in df.iterrows():
        b = r['book']
        running[b] = running.get(b, 0.0) + r['profit']
        snap = {'date': r['date']}
        snap.update({f'balance__{bk}': running[bk] for bk in running})
        rows.append(snap)
    out = pd.DataFrame(rows).drop_duplicates('date').sort_values('date')
    return out

# -------------------------------------------------
# Streamlit UI

st.set_page_config(page_title="Value Betting Tracker", layout="wide")
st.title("🏈 Value Betting Tracker & Bankroll Dashboard")

# Load data
df = load_bets()

# Sidebar: Add Bet Form
st.sidebar.header("➕ Add a New Bet")
with st.sidebar.form("add_bet_form", clear_on_submit=True):
    date = st.date_input("Date", datetime.now())
    sport = st.text_input("Sport", "NBA")
    market = st.text_input("Market", "Moneyline")
    book = st.selectbox("Sportsbook", list(STARTING_BANKROLLS.keys()))
    bet_type = st.selectbox("Bet Type", ["Single", "Parlay", "Future"])
    selection = st.text_input("Selection", "LAL -3")
    odds_american = st.number_input("Odds (American)", value=-110)
    stake = st.number_input("Stake ($)", min_value=0.0, value=10.0)
    result = st.selectbox("Result", ["Pending", "Win", "Loss", "Push"])
    profit = st.number_input("Profit/Loss ($)", value=0.0)
    expected_value = st.number_input("Expected Value (decimal, e.g. 0.05 = +5%)", value=0.0)
    closing_line = st.text_input("Closing Line (optional)", "")
    notes = st.text_area("Notes")
    submitted = st.form_submit_button("Add Bet")
    
    if submitted:
        new_bet = {
            'date': pd.to_datetime(date),
            'sport': sport,
            'market': market,
            'book': book,
            'bet_type': bet_type,
            'selection': selection,
            'odds_american': odds_american,
            'odds_decimal': american_to_decimal(odds_american),
            'stake': stake,
            'result': result,
            'profit': profit,
            'expected_value': expected_value,
            'closing_line': closing_line,
            'notes': notes,
        }
        df = add_bet(df, new_bet)
        st.success(f"Bet added for {sport} on {book}!")

# Main dashboard
if df.empty:
    st.info("No bets yet. Add some in the sidebar to begin tracking.")
    st.stop()

# Metrics
metrics = compute_metrics(df)
cols = st.columns(len(metrics))
for i, (k, v) in enumerate(metrics.items()):
    if 'Rate' in k or 'ROI' in k:
        cols[i].metric(k, f"{v*100:.2f}%")
    else:
        cols[i].metric(k, f"${v:,.2f}")

# Tabs for visualizations
tabs = st.tabs(["📈 Cumulative Profit", "📊 ROI Breakdown", "💰 Bankroll", "⚙️ Data Table"])

with tabs[0]:
    df_sorted = df.sort_values('date')
    fig = px.line(df_sorted, x='date', y='cumulative_profit', title='Cumulative Profit Over Time', markers=True)
    st.plotly_chart(fig, use_container_width=True)

with tabs[1]:
    by_sport = df.groupby('sport').agg({'profit':'sum','stake':'sum'})
    by_sport['ROI'] = by_sport['profit']/by_sport['stake']
    fig1 = px.bar(by_sport.reset_index(), x='sport', y='ROI', title='ROI by Sport')
    st.plotly_chart(fig1, use_container_width=True)

    by_book = df.groupby('book').agg({'profit':'sum','stake':'sum'})
    by_book['ROI'] = by_book['profit']/by_book['stake']
    fig2 = px.bar(by_book.reset_index(), x='book', y='ROI', title='ROI by Sportsbook')
    st.plotly_chart(fig2, use_container_width=True)

with tabs[2]:
    bal_ts = bankroll_simulation(df)
    if not bal_ts.empty:
        melt = bal_ts.melt(id_vars='date', var_name='book', value_name='balance')
        melt['book'] = melt['book'].str.replace('balance__','')
        fig = px.line(melt, x='date', y='balance', color='book', title='Bankroll Over Time by Sportsbook')
        st.plotly_chart(fig, use_container_width=True)

with tabs[3]:
    st.dataframe(df.sort_values('date', ascending=False), use_container_width=True)

st.caption("💡 Tip: Upload to Streamlit Cloud for free hosting and access your tracker anywhere.")
