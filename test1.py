import streamlit as st
import MetaTrader5 as mt5
from datetime import datetime
import pandas as pd
# from database import fetch_symbols, fetch_intervals, fetch_indicators, fetch_periods, load_from_postgresql, save_to_postgresql
# from indicators import calculate_indicators
# from visualization import plot_candlestick_chart, plot_indicators, get_next_color

import psycopg2
import pandas as pd

def get_db_connection():
    """PostgreSQL veritabanına bağlantı sağlar."""
    return psycopg2.connect(
        dbname="mt5_db",
        user="postgres",
        password="123",
        host="localhost",
        port="5432"
    )

def fetch_symbols():
    """Fetch symbols from the symbol_tb table."""
    conn = get_db_connection()
    query = "SELECT symbol FROM symbol_tb;"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df['symbol'].tolist()

def fetch_intervals():
    """Fetch intervals from the interval_tb table."""
    conn = get_db_connection()
    query = "SELECT interval_name, mt5_value FROM interval_tb;"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return dict(zip(df['interval_name'], df['mt5_value']))

def fetch_indicators():
    """Fetch indicators from the indicators_tb table."""
    conn = get_db_connection()
    query = "SELECT indicator_name FROM indicators_tb;"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df['indicator_name'].tolist()

def fetch_periods():
    """Fetch periods from the periods_tb table."""
    conn = get_db_connection()
    query = "SELECT indicator_name, period FROM periods_tb;"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return dict(zip(df['indicator_name'], df['period']))

def load_from_postgresql(symbol, interval):
    """PostgreSQL veritabanından verileri yükler."""
    conn = get_db_connection()
    query = """
        SELECT time, open, high, low, close, upvolume, downvolume, symbol, interval 
        FROM maindata_tb 
        WHERE symbol = %s AND interval = %s
        ORDER BY time ASC;
    """
    df = pd.read_sql_query(query, conn, params=(symbol, interval))
    conn.close()
    df.set_index('time', inplace=True)
    return df

def save_to_postgresql(df, interval, symbol):
    """Verileri PostgreSQL veritabanına kaydeder."""
    conn = get_db_connection()
    cursor = conn.cursor()

    rows_to_insert = []
    for index, row in df.iterrows():
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM maindata_tb 
                WHERE time = %s AND symbol = %s AND interval = %s
            );
        """, (index, row['symbol'], interval))
        exists = cursor.fetchone()[0]

        if not exists:
            rows_to_insert.append(
                (index, row['open'], row['high'], row['low'], row['close'], row['upvolume'], row['downvolume'], row['symbol'], row['interval'])
            )

    if rows_to_insert:
        cursor.executemany("""
            INSERT INTO maindata_tb (time, open, high, low, close, upvolume, downvolume, symbol, interval)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, rows_to_insert)
        conn.commit()

    cursor.close()
    conn.close()

if not mt5.initialize():
    st.error("MetaTrader 5 initialization failed")
    mt5.shutdown()
    exit()

st.title("MT5 Data Fetcher and Technical Indicators")

# Fetch symbols, intervals, indicators, and periods from the database
symbols = fetch_symbols()
intervals = fetch_intervals()
indicators = fetch_indicators()
periods = fetch_periods()

# Kullanıcının seçtiği sembolleri al
selected_symbols = st.multiselect("Select the symbols:", symbols, default=symbols[:3])
start_date = st.date_input("Enter the start date:", datetime(2000, 7, 27))
end_date = st.date_input("Enter the end date:", datetime(2024, 8, 9))

# Zaman dilimi seçenekleri
interval_option = st.selectbox("Select the interval:", list(intervals.keys()))
timeframe = intervals[interval_option]

# İndikatör seçimleri
selected_indicators = st.multiselect("Select the indicators to display:", indicators, default=indicators[:2])

# Renk paleti tanımla
colors = [
    'blue', 'green', 'red', 'cyan', 'magenta', 'yellow', 'purple', 'orange', 'brown',
    'pink', 'gray', 'lime', 'maroon', 'navy', 'olive', 'teal', 'aqua', 'fuchsia', 'gold'
]

if st.button("Fetch Data"):
    fig = go.Figure()
    crossover_dates = []

    for symbol_index, symbol in enumerate(selected_symbols):
        utc_from = datetime.combine(start_date, datetime.min.time())
        utc_to = datetime.combine(end_date, datetime.min.time())

        rates = mt5.copy_rates_range(symbol, timeframe, utc_from, utc_to)

        if rates is None or len(rates) == 0:
            st.error(f"No data found for {symbol} with interval {interval_option}")
            continue

        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        df = df[['open', 'high', 'low', 'close', 'tick_volume']]
        df.rename(columns={'tick_volume': 'upvolume'}, inplace=True)
        df['downvolume'] = df['upvolume'] - df['upvolume'].mean()
        df['symbol'] = symbol
        df['interval'] = interval_option

        # Save to PostgreSQL
        save_to_postgresql(df, interval_option, symbol)

        # # Plot candlestick chart
        # plot_candlestick_chart(df, fig, symbol_index, colors)

        # # Calculate and plot indicators
        # df, crossovers = calculate_indicators(df, selected_indicators, periods)
        # plot_indicators(df, selected_indicators, fig, symbol_index, colors)
        # crossover_dates.extend(crossovers)

    # Display the plot
    st.plotly_chart(fig)
    
    # Display and insert crossover dates into maindata_tb
    if crossover_dates:
        crossover_df = pd.DataFrame(crossover_dates)
        st.subheader("Crossover Dates")
        st.dataframe(crossover_df)
        save_to_postgresql(crossover_df, interval_option, symbol)

    # Load and display data from maindata_tb
    st.subheader("Data from PostgreSQL")
    for symbol in selected_symbols:
        st.write(f"**{symbol}**")
        df_from_db = load_from_postgresql(symbol, interval_option)  
        st.dataframe(df_from_db)

import plotly.graph_objs as go

def plot_candlestick_chart(df, fig, symbol_index, colors):
    """Mum grafiğini çizer ve grafik üzerine ekler."""
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name=f'{df.symbol[0]} Candlestick',
        increasing=dict(line=dict(color='green')),
        decreasing=dict(line=dict(color='red'))
    ))

def plot_indicators(df, indicators, fig, symbol_index, colors):
    """İndikatörleri grafiğe ekler."""
    if "MA20" in indicators:
        fig.add_trace(go.Scatter(x=df.index, y=df['MA_20'], mode='lines', name=f'{df.symbol[0]} MA20',
            line=dict(color=get_next_color(colors, symbol_index + 10))))

    if "MA50" in indicators:
        fig.add_trace(go.Scatter(x=df.index, y=df['MA_50'], mode='lines', name=f'{df.symbol[0]} MA50',
            line=dict(color=get_next_color(colors, symbol_index + 11))))

    # Diğer indikatör çizimleri...

def get_next_color(colors, index):
    """Renk paletinden bir sonraki rengi döndürür."""
    return colors[index % len(colors)]


import numpy as np
import pandas as pd
from datetime import timedelta

def find_crossovers(series1, series2):
    """İki zaman serisi arasındaki kesişim noktalarını bulur."""
    diff = series1 - series2
    crossover_indices = np.where(np.diff(np.sign(diff)))[0] + 1
    return crossover_indices

def remove_duplicate_crossovers(crossover_dates, time_threshold=timedelta(minutes=1)):
    """Kesişim noktaları arasında 1 dakika içinde tekrar olanları iptal eder."""
    unique_dates = []
    last_date = None
    
    for date in sorted(crossover_dates, key=lambda x: x['Date']):
        if last_date is None or (date['Date'] - last_date) > time_threshold:
            unique_dates.append(date)
            last_date = date['Date']
    
    return unique_dates

def calculate_indicators(df, indicators, periods):
    """Seçili indikatörlere göre verileri hesaplar ve crossover noktalarını bulur."""
    crossover_dates = []
    df = df[df.index.to_series().dt.dayofweek < 5]  # Hafta sonları kapalı olan günleri hariç tutma
    
    if "MA20" in indicators:
        period = periods.get("MA20", 20)
        df['MA_20'] = df['close'].rolling(window=period).mean()
        
    if "MA50" in indicators:
        period = periods.get("MA50", 50)
        df['MA_50'] = df['close'].rolling(window=period).mean()

        if "MA20" in indicators:
            valid_dates = df.dropna(subset=['MA_20', 'MA_50']).index
            ma20_valid = df['MA_20'].reindex(valid_dates)
            ma50_valid = df['MA_50'].reindex(valid_dates)
            
            ma_crossover_indices = find_crossovers(ma20_valid, ma50_valid)
            ma_crossover_times = valid_dates[ma_crossover_indices]

            crossover_dates.extend({
                'Symbol': df.symbol[0],
                'Date': time,
                'First Intersecting Indicators': 'MA20',
                'Second Intersecting Indicators': 'MA50',
                'Signal': 'Buy' if df['MA_20'].loc[time] > df['MA_50'].loc[time] else 'Sell',
                'Price': df['close'].loc[time],
                'interval': df['interval'][0]
            } for time in ma_crossover_times)

    # Diğer indikatör hesaplamaları ve crossover analizleri...

    return df, remove_duplicate_crossovers(crossover_dates)