import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
import psycopg2
import streamlit as st
import plotly.graph_objs as go
import numpy as np
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

def get_db_connection():
    """PostgreSQL veritabanına bağlan."""
    try:
        conn = psycopg2.connect(
            dbname="mt5_db",
            user="postgres",
            password="123",
            host="localhost",
            port="5432"
        )
        return conn
    except Exception as e:
        logging.error(f"Database'e bağlanırken hata: {e}")
        st.error("Database'e bağlanırken hata. Logları kontrol edin.")
        raise

def fetch_data(table_name):
    """Tablolardan verileri alır."""
    conn = get_db_connection()
    query = f"SELECT * FROM {table_name};"
    try:
        with conn.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
    except Exception as e:
        logging.error(f"Veriler alınırken hata oluştu: {table_name}: {e}")
        st.error(f"Veriler alınırken hata oluştu: {table_name}. Logları kontrol edin.")
        return []
    finally:
        conn.close()
    return rows

def display_multiselect(title, data, key):
    """Streamlit multiselect oluştur ve seçilen değerleri göster."""
    if data:
        selected_options = st.multiselect(title, data, key=key)
        return selected_options
    else:
        st.write(f"{title} bulunamadı.")
        return []

def get_default_values():
    """Varsayılan sembolleri, indikatörleri, interval ve periyotları veritabanından al."""
    symbols = fetch_data('symbol_tb')
    indicators = fetch_data('indicators_tb')
    intervals = fetch_data('interval_tb')
    periods = fetch_data('periods_tb')

    return {
        'symbols': [row[1] for row in symbols] if symbols else [],
        'indicators': [row[1] for row in indicators] if indicators else [],
        'intervals': [row[1] for row in intervals] if intervals else [],
        'periods': [row[1] for row in periods] if periods else []
    }

# Varsayılan değerleri session_state'e yerleştir
default_values = get_default_values()
for key, value in default_values.items():
    st.session_state[key] = st.session_state.get(key, value)

# Streamlit interface
st.title("MT5 Data Fetcher and Technical Indicators")

selected_symbol = display_multiselect('Sembol Seçin', st.session_state['symbols'], key='symbol_selectbox')
selected_interval = display_multiselect('Interval Seçin', st.session_state['intervals'], key='interval_selectbox')
selected_indicator = display_multiselect('İndikatör Seçin', st.session_state['indicators'], key='indicator_selectbox')
selected_period = display_multiselect('Periyot Seçin', st.session_state['periods'], key='period_selectbox')
start_date = st.date_input("Başlangıç tarihini girin:", datetime(2024, 7, 27))
end_date = st.date_input("Bitiş tarihini girin:", datetime(2024, 7, 28))

# Timeframe belirleme: Eğer selected_interval None ise, intervals listesinin ilk elemanını kullan
timeframe = selected_interval if selected_interval in st.session_state['intervals'] else st.session_state['intervals'][0]

if not mt5.initialize():
    st.error("MetaTrader 5 initialization failed")
    mt5.shutdown()
    st.stop()

def load_from_postgresql(symbol, interval):
    """PostgreSQL veritabanından verileri yükler."""
    conn = get_db_connection()
    query = """
        SELECT time, open, high, low, close, upvolume, downvolume, symbol, interval 
        FROM mt5_tb 
        WHERE symbol = %s AND interval = %s
        ORDER BY time ASC;
    """
    try:
        df = pd.read_sql_query(query, conn, params=(symbol, interval))
    except Exception as e:
        logging.error(f"Error loading data from PostgreSQL: {e}")
        st.error("Error loading data from PostgreSQL. Check logs for details.")
        return pd.DataFrame()
    finally:
        conn.close()
    df.set_index('time', inplace=True)
    return df

def save_to_postgresql(df, interval, symbol, start_date, end_date):
    """Verileri PostgreSQL veritabanına kaydeder, varsa mevcut kayıtları kontrol eder."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        data_exists = False
        for index, row in df.iterrows():
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM mt5_tb 
                    WHERE time = %s AND symbol = %s AND interval = %s
                );
            """, (index, row['symbol'], interval))
            exists = cursor.fetchone()[0]
            if exists:
                data_exists = True
            else:
                cursor.execute("""
                    INSERT INTO mt5_tb (time, open, high, low, close, upvolume, downvolume, symbol, interval)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (index, row['open'], row['high'], row['low'], row['close'], row['upvolume'], row['downvolume'], row['symbol'], row['interval']))
        conn.commit()
    except Exception as e:
        logging.error(f"Error saving data to PostgreSQL: {e}")
        st.error("Error saving data to PostgreSQL. Check logs for details.")
    finally:
        cursor.close()
        conn.close()
    if data_exists:
        st.error(f"DB'de {symbol} sembolü, {interval} intervali ve {start_date} - {end_date} tarih aralığı için veri bulunuyor")
    else:
        st.success(f"DB'de {symbol} sembolü, {interval} intervali ve {start_date} - {end_date} tarih aralığı için veri bulunmuyor")

def insert_crossover_dates(crossover_dates):
    """Crossover tarihlerini PostgreSQL veritabanına ekler."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        for record in crossover_dates:
            cursor.execute("""
                INSERT INTO maindata_tb (symbol, date, Signal, Price, interval, indicators) 
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (symbol, date) DO NOTHING;
            """, (record['Symbol'], record['Date'], record['Signal'], record['Price'], record['interval'], record['Indicators']))
        conn.commit()
    except Exception as e:
        logging.error(f"Error inserting crossover dates: {e}")
        st.error("Error inserting crossover dates. Check logs for details.")
    finally:
        cursor.close()
        conn.close()

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

def get_next_color(colors, index):
    """Renk döngüsü fonksiyonu"""
    return colors[index % len(colors)]

def plot_indicators(df, indicators, fig, symbol_index, colors):
    """İndikatörleri hesaplar ve grafiğe ekler, kesişim noktalarını bulur ve veritabanına ekler."""
    crossover_dates = []

    # Hafta sonları kapalı olduğu için, cumartesi ve pazar günlerini kapalı olarak ekleyin
    weekend_days = [5, 6]
    start_date = df.index.min()
    end_date = df.index.max()

    for date in pd.date_range(start=start_date, end=end_date):
        if date.weekday() in weekend_days:
            df.loc[date] = [np.nan] * df.shape[1]

    for ind_index, indicator in enumerate(indicators):
        if indicator.startswith("MA"):
            period = int(indicator[2:])
            df[indicator] = df['close'].rolling(window=period).mean()
        elif indicator.startswith("EMA"):
            period = int(indicator[3:])
            df[indicator] = df['close'].ewm(span=period, adjust=False).mean()
        elif indicator.startswith("SMA"):
            period = int(indicator[3:])
            df[indicator] = df['close'].rolling(window=period).mean()
        elif indicator.startswith("WMA"):
            period = int(indicator[3:])
            weights = np.arange(1, period + 1)
            df[indicator] = df['close'].rolling(window=period).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)
        else:
            logging.warning(f"Unknown indicator: {indicator}")
            continue

        color = get_next_color(colors, ind_index)

        if indicator in df.columns:
            # Grafik ekleme
            fig.add_trace(go.Scatter(x=df.index, y=df[indicator], mode='lines', name=f"{indicator} ({symbol_index})", line=dict(color=color)))
        else:
            logging.warning(f"Indicator {indicator} not found in DataFrame.")

        # MA ve EMA arasındaki kesişim noktalarını bulma
        if indicator.startswith(("MA", "EMA")):
            for other_ind_index in range(ind_index + 1, len(indicators)):
                other_indicator = indicators[other_ind_index]
                if other_indicator in df.columns:
                    crossover_indices = find_crossovers(df[indicator], df[other_indicator])
                    for idx in crossover_indices:
                        crossover_date = df.index[idx]
                        signal = "Buy" if df[indicator][idx] < df[other_indicator][idx] else "Sell"
                        crossover_dates.append({
                            'Symbol': symbol_index,
                            'Date': crossover_date,
                            'Signal': signal,
                            'Price': df['close'][idx],
                            'interval': timeframe,
                            'Indicators': f"{indicator}-{other_indicator}"
                        })

    # Kesişim noktalarını veritabanına kaydetme
    unique_crossovers = remove_duplicate_crossovers(crossover_dates)
    insert_crossover_dates(unique_crossovers)

    return fig

def plot_data(symbol, interval):
    """Veri kaynağını seçip grafiği çizer."""
    with st.spinner("Veriler yükleniyor..."):
        df = load_from_postgresql(symbol, interval)
        if df.empty:
            st.error("Veritabanından veri alınamadı.")
            return

    fig = go.Figure()

    # Ana sembol grafiği
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name="Candlestick"
    ))

    # Grafik renkleri
    colors = ['blue', 'green', 'red', 'purple', 'orange', 'cyan']

    # İndikatör grafikleri ve kesişim noktaları
    if selected_indicator:
        plot_indicators(df, selected_indicator, fig, symbol, colors)

    fig.update_layout(
        title=f"{symbol} - {interval}",
        xaxis_title="Tarih",
        yaxis_title="Fiyat",
        xaxis_rangeslider_visible=False
    )

    st.plotly_chart(fig)

#Gösterim için buton
if st.button('Veriyi Göster'):
    if selected_symbol and selected_interval:
        plot_data(selected_symbol, selected_interval)
    else:
        st.warning("Lütfen sembol ve interval seçin.")
