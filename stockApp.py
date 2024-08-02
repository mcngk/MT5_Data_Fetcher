import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
import psycopg2
import streamlit as st
import plotly.graph_objs as go
import numpy as np

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
        SELECT time, open, high, low, close, upvolume, downvolume, symbol, interval 
        FROM mt5_db 
        WHERE symbol = %s AND interval = %s
        ORDER BY time ASC;
    """
    df = pd.read_sql_query(query, conn, params=(symbol, interval))
    conn.close()
    df.set_index('time', inplace=True)
    return df

def save_to_postgresql(df, interval, symbol, start_date, end_date):
    """Verileri PostgreSQL veritabanına kaydeder, varsa mevcut kayıtları kontrol eder."""
    conn = get_db_connection()
    cursor = conn.cursor()
    data_exists = False

    for index, row in df.iterrows():
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM mt5_db 
                WHERE time = %s AND symbol = %s AND interval = %s
            );
        """, (index, row['symbol'], interval))
        exists = cursor.fetchone()[0]

        if exists:
            data_exists = True
        else:
            cursor.execute("""
                INSERT INTO mt5_db (time, open, high, low, close, upvolume, downvolume, symbol, interval)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (index, row['open'], row['high'], row['low'], row['close'], row['upvolume'], row['downvolume'], row['symbol'], row['interval']))

    conn.commit()
    cursor.close()
    conn.close()

    if data_exists:
        st.error(f"DB'de {symbol} sembolü, {interval_option} intervali ve {start_date} - {end_date} tarih aralığı için veri bulunuyor")
    else:
        st.success(f"DB'de {symbol} sembolü, {interval_option} intervali ve {start_date} - {end_date} tarih aralığı için veri bulunmuyor")

def insert_crossover_dates(crossover_dates):
    """Crossover tarihlerini PostgreSQL veritabanına ekler."""
    conn = get_db_connection()
    cursor = conn.cursor()
    for record in crossover_dates:
        # 'record['Date']' tarih ve saat bilgilerini içermeli
        cursor.execute("""
            INSERT INTO crossover_dates_tb (symbol, date) VALUES (%s, %s)
            ON CONFLICT (symbol, date) DO NOTHING;
        """, (record['Symbol'], record['Date']))
    conn.commit()
    cursor.close()
    conn.close()

# Streamlit arayüzünü oluştur
st.title("MT5 Data Fetcher and Technical Indicators")

# Varsayılan semboller
default_symbols = ["XAUUSD", "XAUEUR"]

# Kullanıcının seçtiği sembolleri al
symbols = st.session_state.get('symbols', default_symbols)

# Kullanıcıdan sembol ve tarih aralığını al
selected_symbols = st.multiselect("Select the symbols:", symbols, default=symbols)
start_date = st.date_input("Enter the start date:", datetime(2024, 7, 27))
end_date = st.date_input("Enter the end date:", datetime(2024, 7, 28))

# Zaman dilimi seçenekleri
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

# İndikatör seçimleri
indicators = st.multiselect("Select the indicators to display:", ["MA", "MACD", "RSI", "SMA", "EMA", "WMA"], default=["MA", "MACD", "RSI", "SMA", "EMA", "WMA"])

# Renk paleti tanımla
colors = ["blue", "red", "green", "orange", "purple"]

def get_next_color(colors, index):
    """Renk paletinden döngüsel olarak renk seç."""
    return colors[index % len(colors)]


def find_crossovers(series1, series2):
    """
    İki zaman serisi arasındaki kesişim noktalarını bulur.
    """
    diff = series1 - series2
    crossover_indices = np.where(np.diff(np.sign(diff)))[0] + 1
    return crossover_indices

if st.button("Fetch Data"):
    fig = go.Figure()
    crossover_dates = []  # Crossover tarihlerini saklamak için bir liste

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

        save_to_postgresql(df, interval_option, symbol, start_date, end_date)

        # Candlestick Chart
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name=f'{symbol} Candlestick',
            increasing=dict(line=dict(color='green')),
            decreasing=dict(line=dict(color='red'))
        ))

        # MA
        if "MA" in indicators:
            df['MA_14'] = df['close'].rolling(window=14).mean()
            df['MA_30'] = df['close'].rolling(window=30).mean()

            fig.add_trace(go.Scatter(x=df.index, y=df['MA_14'], mode='lines', name=f'{symbol} MA 14',
                line=dict(color=get_next_color(colors, symbol_index + 10))))
            fig.add_trace(go.Scatter(x=df.index, y=df['MA_30'], mode='lines', name=f'{symbol} MA 30',
                line=dict(color=get_next_color(colors, symbol_index + 11))))

            ma_crossover_indices = find_crossovers(df['MA_14'].dropna(), df['MA_30'].dropna())
            ma_crossover_indices = ma_crossover_indices.astype(int)
            ma_crossover_times = df.index[df.index.isin(df['MA_14'].dropna().index[ma_crossover_indices])]

            fig.add_trace(go.Scatter(
                x=ma_crossover_times,
                y=df['MA_14'].reindex(ma_crossover_times),
                mode='markers',
                marker=dict(symbol='x', color='cyan', size=10),
                name=f'{symbol} MA Crossovers'
            ))

            crossover_dates.extend({'Symbol': symbol, 'Date': time} for time in ma_crossover_times)

        # SMA
        if "SMA" in indicators:
            df['SMA_30'] = df['close'].rolling(window=30).mean()
            df['SMA_50'] = df['close'].rolling(window=50).mean()

            fig.add_trace(go.Scatter(x=df.index, y=df['SMA_30'], mode='lines', name=f'{symbol} SMA 30',
                line=dict(color=get_next_color(colors, symbol_index + 1))))
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], mode='lines', name=f'{symbol} SMA 50',
                line=dict(color=get_next_color(colors, symbol_index + 2))))

            sma_crossover_indices = find_crossovers(df['SMA_30'].dropna(), df['SMA_50'].dropna())
            sma_crossover_indices = sma_crossover_indices.astype(int)
            sma_crossover_times = df.index[df.index.isin(df['SMA_30'].dropna().index[sma_crossover_indices])]

            fig.add_trace(go.Scatter(
                x=sma_crossover_times,
                y=df['SMA_30'].reindex(sma_crossover_times),
                mode='markers',
                marker=dict(symbol='x', color='blue', size=10),
                name=f'{symbol} SMA Crossovers'
            ))

            crossover_dates.extend({'Symbol': symbol, 'Date': time} for time in sma_crossover_times)

        # EMA
        if "EMA" in indicators:
            df['EMA_12'] = df['close'].ewm(span=12, adjust=False).mean()
            df['EMA_26'] = df['close'].ewm(span=26, adjust=False).mean()

            fig.add_trace(go.Scatter(x=df.index, y=df['EMA_12'], mode='lines', name=f'{symbol} EMA 12',
                line=dict(color=get_next_color(colors, symbol_index + 3))))
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA_26'], mode='lines', name=f'{symbol} EMA 26',
                line=dict(color=get_next_color(colors, symbol_index + 4))))

            ema_crossover_indices = find_crossovers(df['EMA_12'].dropna(), df['EMA_26'].dropna())
            ema_crossover_indices = ema_crossover_indices.astype(int)
            ema_crossover_times = df.index[df.index.isin(df['EMA_12'].dropna().index[ema_crossover_indices])]

            fig.add_trace(go.Scatter(
                x=ema_crossover_times,
                y=df['EMA_12'].reindex(ema_crossover_times),
                mode='markers',
                marker=dict(symbol='x', color='orange', size=10),
                name=f'{symbol} EMA Crossovers'
            ))

            crossover_dates.extend({'Symbol': symbol, 'Date': time} for time in ema_crossover_times)

        # WMA
        if "WMA" in indicators:
            df['WMA_14'] = df['close'].rolling(window=14).apply(lambda x: (x * range(1, 15)).sum() / sum(range(1, 15)))
            df['WMA_30'] = df['close'].rolling(window=30).apply(lambda x: (x * range(1, 31)).sum() / sum(range(1, 31)))

            fig.add_trace(go.Scatter(x=df.index, y=df['WMA_14'], mode='lines', name=f'{symbol} WMA 14',
                line=dict(color=get_next_color(colors, symbol_index + 5))))
            fig.add_trace(go.Scatter(x=df.index, y=df['WMA_30'], mode='lines', name=f'{symbol} WMA 30',
                line=dict(color=get_next_color(colors, symbol_index + 6))))

            wma_crossover_indices = find_crossovers(df['WMA_14'].dropna(), df['WMA_30'].dropna())
            wma_crossover_indices = wma_crossover_indices.astype(int)
            wma_crossover_times = df.index[df.index.isin(df['WMA_14'].dropna().index[wma_crossover_indices])]

            fig.add_trace(go.Scatter(
                x=wma_crossover_times,
                y=df['WMA_14'].reindex(wma_crossover_times),
                mode='markers',
                marker=dict(symbol='x', color='purple', size=10),
                name=f'{symbol} WMA Crossovers'
            ))

            crossover_dates.extend({'Symbol': symbol, 'Date': time} for time in wma_crossover_times)

        # MACD
        if "MACD" in indicators:
            short_ema = df['close'].ewm(span=12, adjust=False).mean()
            long_ema = df['close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = short_ema - long_ema
            df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()

            fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], mode='lines', name=f'{symbol} MACD',
                line=dict(color=get_next_color(colors, symbol_index + 7))))
            fig.add_trace(go.Scatter(x=df.index, y=df['Signal_Line'], mode='lines', name=f'{symbol} Signal Line',
                line=dict(color=get_next_color(colors, symbol_index + 8))))

        # RSI
        if "RSI" in indicators:
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0).rolling(window=14).mean()
            loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))

            fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], mode='lines', name=f'{symbol} RSI',
                line=dict(color=get_next_color(colors, symbol_index + 9))))

    # Tüm grafiği göster
    st.plotly_chart(fig)

    # Crossover tarihlerini tablosunu göster ve PostgreSQL'e ekle
    if crossover_dates:
        crossover_df = pd.DataFrame(crossover_dates)
        st.subheader("Crossover Dates")
        st.dataframe(crossover_df)

        insert_crossover_dates(crossover_dates)

    # PostgreSQL'den veri çek ve göster
    st.subheader("Data from PostgreSQL")
    for symbol in selected_symbols:
        st.write(f"**{symbol}**")
        df_from_db = load_from_postgresql(symbol, interval_option)
        st.dataframe(df_from_db)

# MetaTrader 5 terminal bağlantısını kapat
mt5.shutdown()