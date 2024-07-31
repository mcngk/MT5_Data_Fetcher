import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
import psycopg2
import streamlit as st
import plotly.graph_objs as go

# MetaTrader 5 terminaline bağlantıyı başlat
if not mt5.initialize():
    st.error("MetaTrader 5 initialization failed")
    mt5.shutdown()
    exit()

def get_db_connection():
    """PostgreSQL veritabanına bağlantı sağlar."""
    return psycopg2.connect(
        dbname="mt5_db",
        user="postgres",
        password="123",
        host="localhost",
        port="5432"
    )

def load_from_postgresql(symbol, interval):
    """PostgreSQL veritabanından verileri yükler."""
    conn = get_db_connection()
    query = """
        SELECT time, open, high, low, close, tick_volume, symbol, interval 
        FROM mt5_db 
        WHERE symbol = %s AND interval = %s
        ORDER BY time ASC;
    """
    df = pd.read_sql_query(query, conn, params=(symbol, interval))
    conn.close()
    df.set_index('time', inplace=True)
    return df

def save_to_postgresql(df, interval):
    """Verileri PostgreSQL veritabanına kaydeder, varsa mevcut kayıtları kontrol eder."""
    conn = get_db_connection()
    cursor = conn.cursor()

    for index, row in df.iterrows():
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM mt5_db 
                WHERE time = %s AND symbol = %s AND interval = %s
            );
        """, (index, row['symbol'], interval))
        exists = cursor.fetchone()[0]

        if not exists:
            cursor.execute("""
                INSERT INTO mt5_db (time, open, high, low, close, tick_volume, symbol, interval)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (index, row['open'], row['high'], row['low'], row['close'], row['tick_volume'], row['symbol'], row['interval']))

    conn.commit()
    cursor.close()
    conn.close()

st.title("MT5 Data Fetcher and Technical Indicators")

default_symbols = ["XAUUSD", "XAUEUR"]
symbols = st.session_state.get('symbols', default_symbols)

selected_symbols = st.multiselect("Select the symbols:", symbols, default=symbols)
start_date = st.date_input("Enter the start date:", datetime(2024, 7, 27))
end_date = st.date_input("Enter the end date:", datetime(2024, 7, 28))

intervals = {
    "1 minute": mt5.TIMEFRAME_M1,
    "5 minutes": mt5.TIMEFRAME_M5,
    "15 minutes": mt5.TIMEFRAME_M15,
    "30 minutes": mt5.TIMEFRAME_M30,
    "1 hour": mt5.TIMEFRAME_H1,
    "4 hours": mt5.TIMEFRAME_H4,
    "1 day": mt5.TIMEFRAME_D1
}

interval_option = st.selectbox("Select the interval:", list(intervals.keys()))
timeframe = intervals[interval_option]

indicators = st.multiselect("Select the indicators to display:", ["MA", "MACD", "RSI", "SMA", "EMA", "WMA"], default=["MA", "MACD", "RSI", "SMA", "EMA", "WMA"])

colors = ["blue", "red", "green", "orange", "purple"]

def get_next_color(colors, index):
    """Renk paletinden döngüsel olarak renk seç."""
    return colors[index % len(colors)]

if st.button("Fetch Data"):
    fig_price = go.Figure()
    fig_macd = go.Figure()
    fig_rsi = go.Figure()

    all_data = []

    for symbol_index, symbol in enumerate(selected_symbols):
        utc_from = datetime.combine(start_date, datetime.min.time())
        utc_to = datetime.combine(end_date, datetime.min.time())

        rates = mt5.copy_rates_range(symbol, timeframe, utc_from, utc_to)

        if rates is None or len(rates) == 0:
            st.error(f"No data found for {symbol}")
            continue

        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        df = df[['open', 'high', 'low', 'close', 'tick_volume']]
        df['symbol'] = symbol
        df['interval'] = interval_option

        all_data.append(df)
        save_to_postgresql(df, interval_option)

        fig_price.add_trace(go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name=f'{symbol} Candlestick'
        ))

        if "SMA" in indicators:
            df['SMA_30'] = df['close'].rolling(window=30).mean()
            df['SMA_50'] = df['close'].rolling(window=50).mean()
            fig_price.add_trace(go.Scatter(x=df.index, y=df['SMA_30'], mode='lines', name=f'{symbol} SMA 30', 
                line=dict(color=get_next_color(colors, symbol_index + 1))))
            fig_price.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], mode='lines', name=f'{symbol} SMA 50',
                line=dict(color=get_next_color(colors, symbol_index + 2))))

        if "EMA" in indicators:
            df['EMA_12'] = df['close'].ewm(span=12, adjust=False).mean()
            df['EMA_26'] = df['close'].ewm(span=26, adjust=False).mean()
            fig_price.add_trace(go.Scatter(x=df.index, y=df['EMA_12'], mode='lines', name=f'{symbol} EMA 12', 
                line=dict(color=get_next_color(colors, symbol_index + 3))))
            fig_price.add_trace(go.Scatter(x=df.index, y=df['EMA_26'], mode='lines', name=f'{symbol} EMA 26',
                line=dict(color=get_next_color(colors, symbol_index + 4))))

        if "WMA" in indicators:
            df['WMA_14'] = df['close'].rolling(window=14).apply(lambda x: (x * range(1, 15)).sum() / sum(range(1, 15)))
            df['WMA_30'] = df['close'].rolling(window=30).apply(lambda x: (x * range(1, 31)).sum() / sum(range(1, 31)))
            fig_price.add_trace(go.Scatter(x=df.index, y=df['WMA_14'], mode='lines', name=f'{symbol} WMA 14', 
                line=dict(color=get_next_color(colors, symbol_index + 5))))
            fig_price.add_trace(go.Scatter(x=df.index, y=df['WMA_30'], mode='lines', name=f'{symbol} WMA 30',
                line=dict(color=get_next_color(colors, symbol_index + 6))))

        if "MACD" in indicators:
            short_ema = df['close'].ewm(span=12, adjust=False).mean()
            long_ema = df['close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = short_ema - long_ema
            df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
            fig_macd.add_trace(go.Scatter(x=df.index, y=df['MACD'], mode='lines', name=f'{symbol} MACD',
                line=dict(color=get_next_color(colors, symbol_index))))
            fig_macd.add_trace(go.Scatter(x=df.index, y=df['Signal_Line'], mode='lines', name=f'{symbol} Signal Line',
                line=dict(color=get_next_color(colors, symbol_index + 1))))

        if "RSI" in indicators:
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            avg_gain = gain.rolling(window=14).mean()
            avg_loss = loss.rolling(window=14).mean()
            rs = avg_gain / avg_loss
            df['RSI'] = 100 - (100 / (1 + rs))
            fig_rsi.add_trace(go.Scatter(x=df.index, y=df['RSI'], mode='lines', name=f'{symbol} RSI',
                line=dict(color=get_next_color(colors, symbol_index))))

    fig_price.update_layout(template="plotly_dark", height=400, transition_duration=500)
    fig_macd.update_layout(template="plotly_dark", height=300, transition_duration=500)
    fig_rsi.update_layout(template="plotly_dark", height=300, transition_duration=500)

    st.plotly_chart(fig_price)
    st.plotly_chart(fig_macd)
    st.plotly_chart(fig_rsi)

    st.subheader("Data from PostgreSQL")
    for symbol in selected_symbols:
        st.write(f"**{symbol}**")
        df_from_db = load_from_postgresql(symbol, interval_option)
        st.dataframe(df_from_db)

mt5.shutdown()
