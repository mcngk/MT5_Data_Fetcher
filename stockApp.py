import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
import streamlit as st
import plotly.graph_objs as go
import numpy as np
import psycopg2

# # MetaTrader 5 terminaline bağlanın
# login = 51890414
# password = 'D9sYWpr&NwN!nY'
# server = "ICMarketsEU-Demo"

# # MetaTrader 5 hesabına giriş yapın
# if not mt5.login(login, password=password, server=server):
#     st.error("MetaTrader 5 login failed")
#     mt5.shutdown()
#     exit()

# PostgreSQL bağlantı bilgileri
def get_db_connection():
    return psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password="123",
        host="localhost",
        port="5432"
    )

# Verileri veritabanına yazma işlevi
def write_to_db(df, table_name):
    conn = get_db_connection()
    cur = conn.cursor()
    
    create_table_query = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        time TIMESTAMP,
        open FLOAT,
        high FLOAT,
        low FLOAT,
        close FLOAT,
        tick_volume INT,
        symbol VARCHAR(10)
    )
    """
    cur.execute(create_table_query)
    conn.commit()

    # Verileri tabloya ekle
    for index, row in df.iterrows():
        insert_query = f"""
        INSERT INTO {table_name} (time, open, high, low, close, tick_volume, symbol) 
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cur.execute(insert_query, (row.name, row['open'], row['high'], row['low'], row['close'], row['tick_volume'], row['symbol']))
    
    conn.commit()
    cur.close()
    conn.close()

# Streamlit arayüzü
st.title("MT5 and Technical Indicators")

# Varsayılan semboller
default_symbols = ["XAUUSD", "XAUEUR"]

# Kullanıcıdan sembol ekleme işlemleri
symbols = st.session_state.get('symbols', default_symbols)

# Kullanıcıdan sembol ve tarih aralığını al
selected_symbols = st.multiselect("Select the symbols:", symbols, default=symbols)
start_date = st.date_input("Enter the start date:", datetime(2024, 7, 24))
end_date = st.date_input("Enter the end date:", datetime(2024, 7, 25))

# Interval seçenekleri
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
indicators = st.multiselect("Select the indicators to display:", ["MA", "MACD", "RSI"], default=["MA"])

# Renk paleti
colors = ["blue", "red", "green", "orange", "purple"]

def get_next_color(colors, index):
    return colors[index % len(colors)]

# Verileri çekmek ve listelemek için buton
if st.button("Fetch Data"):
    fig_price_ma = go.Figure()
    fig_macd = go.Figure()
    fig_rsi = go.Figure()

    all_data = []  # Verilerin tutulacağı liste

    for symbol_index, symbol in enumerate(selected_symbols):
        # Tarihleri datetime formatına çevir
        utc_from = datetime.combine(start_date, datetime.min.time())
        utc_to = datetime.combine(end_date, datetime.min.time())

        # Tarihsel verileri çek
        rates = mt5.copy_rates_range(symbol, timeframe, utc_from, utc_to)

        if rates is None or len(rates) == 0:
            st.error(f"No data found for {symbol}")
            continue

        # Verileri DataFrame'e dönüştür
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        df = df[['open', 'high', 'low', 'close', 'tick_volume']]
        df['symbol'] = symbol  # Sembol bilgisi ekle

        # Verileri listeye ekle
        all_data.append(df)

        # Verileri veritabanına yaz
        write_to_db(df, 'symbol_data')

        # Renk seçimi
        color = get_next_color(colors, symbol_index)

        if "MA" in indicators:
            # MA hesaplama (30 ve 50 günlük)
            df['MA_30'] = df['close'].rolling(window=30).mean()
            df['MA_50'] = df['close'].rolling(window=50).mean()

            # Fiyat grafiği ve MA çizgileri
            fig_price_ma.add_trace(go.Scatter(x=df.index, y=df['close'], mode='lines', name=f'{symbol} Close Price', line=dict(color=color)))
            fig_price_ma.add_trace(go.Scatter(x=df.index, y=df['MA_30'], mode='lines', name=f'{symbol} MA 30', line=dict(color=get_next_color(colors, symbol_index + 1))))
            fig_price_ma.add_trace(go.Scatter(x=df.index, y=df['MA_50'], mode='lines', name=f'{symbol} MA 50', line=dict(color=get_next_color(colors, symbol_index + 2))))

        if "MACD" in indicators:
            # MACD hesaplama
            short_ema = df['close'].ewm(span=12, adjust=False).mean()
            long_ema = df['close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = short_ema - long_ema
            df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()

            # MACD ve Signal Line grafikleri
            fig_macd.add_trace(go.Scatter(x=df.index, y=df['MACD'], mode='lines', name=f'{symbol} MACD', line=dict(color=color)))
            fig_macd.add_trace(go.Scatter(x=df.index, y=df['Signal_Line'], mode='lines', name=f'{symbol} Signal Line', line=dict(color=get_next_color(colors, symbol_index + 1))))

        if "RSI" in indicators:
            # RSI hesaplama
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))

            # RSI grafiği
            fig_rsi.add_trace(go.Scatter(x=df.index, y=df['RSI'], mode='lines', name=f'{symbol} RSI', line=dict(color=color)))

    # Verileri birleştir
    combined_df = pd.concat(all_data)

    # Veri çerçevesini görüntüle
    st.write("### Combined Data")
    st.write(combined_df)

    # Grafiklerin başlıkları ve eksen etiketleri
    if "MA" in indicators:
        fig_price_ma.update_layout(
            title='Price and Moving Averages',
            xaxis_title='Date',
            yaxis_title='Price',
            yaxis=dict(
                rangemode="tozero"  # Y eksenini minimum değerle sıfırlamak için
            )
        )
        st.plotly_chart(fig_price_ma)

    if "MACD" in indicators:
        fig_macd.update_layout(
            title='MACD and Signal Line',
            xaxis_title='Date',
            yaxis_title='MACD Value'
        )
        st.plotly_chart(fig_macd)

    if "RSI" in indicators:
        fig_rsi.add_hline(y=70, line_dash="dash", line_color="red")
        fig_rsi.add_hline(y=30, line_dash="dash", line_color="blue")
        fig_rsi.update_layout(
            title='RSI Indicator',
            xaxis_title='Date',
            yaxis_title='RSI Value'
        )
        st.plotly_chart(fig_rsi)

# MetaTrader 5 terminal bağlantısını kapatın
mt5.shutdown()
