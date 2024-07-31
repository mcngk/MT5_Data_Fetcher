import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
import psycopg2
import streamlit as st
import plotly.graph_objs as go

# MetaTrader 5 terminaline bağlantıyı başlat
if not mt5.initialize():
    st.error("MetaTrader 5 initialization failed")  # Bağlantı başarısızsa hata mesajı göster
    mt5.shutdown()  # MetaTrader 5 terminalini kapat
    exit()  # Programı sonlandır

# PostgreSQL veritabanı bağlantı bilgilerini döndüren fonksiyon
def get_db_connection():
    """PostgreSQL veritabanına bağlantı sağlar."""
    return psycopg2.connect(
        dbname="mt5_db",  # Veritabanı adı
        user="postgres",  # Kullanıcı adı
        password="123",  # Şifre
        host="localhost",  # Host adresi
        port="5432"  # Port numarası
    )

def load_from_postgresql(symbol, interval):
    """PostgreSQL veritabanından verileri yükler."""
    conn = get_db_connection()  # Veritabanı bağlantısını al
    query = """
        SELECT time, open, high, low, close, tick_volume, symbol, interval 
        FROM mt5_db 
        WHERE symbol = %s AND interval = %s
        ORDER BY time ASC;
    """
    df = pd.read_sql_query(query, conn, params=(symbol, interval))  # SQL sorgusunu çalıştır ve verileri DataFrame'e al
    conn.close()  # Veritabanı bağlantısını kapat
    df.set_index('time', inplace=True)  # Zamanı index olarak ayarla
    return df

def save_to_postgresql(df, interval):
    """Verileri PostgreSQL veritabanına kaydeder, varsa mevcut kayıtları kontrol eder."""
    conn = get_db_connection()  # Veritabanı bağlantısını al
    cursor = conn.cursor()  # SQL komutlarını çalıştırmak için cursor oluştur

    for index, row in df.iterrows():  # DataFrame'deki her satırı döngüye al 
        # Önce mevcut kayıtları kontrol et
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM mt5_db 
                WHERE time = %s AND symbol = %s AND interval = %s
            );
        """, (index, row['symbol'], interval))
        exists = cursor.fetchone()[0] #SQL sorgusunun sonucunda dönen verinin ilk sütununu almak için kullanılır.

        if not exists:
            # Eğer kayıt mevcut değilse, yeni veriyi ekle
            cursor.execute("""
                INSERT INTO mt5_db (time, open, high, low, close, tick_volume, symbol, interval)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (index, row['open'], row['high'], row['low'], row['close'], row['tick_volume'], row['symbol'], row['interval']))

    conn.commit()  # Değişiklikleri veritabanına kaydet
    cursor.close()  # Cursor'ı kapat
    conn.close()  # Veritabanı bağlantısını kapat

# Streamlit arayüzünü oluştur
st.title("MT5 Data Fetcher and Technical Indicators")  # Uygulama başlığını belirle

# Varsayılan semboller
default_symbols = ["XAUUSD", "XAUEUR"]

# Kullanıcının seçtiği sembolleri al
symbols = st.session_state.get('symbols', default_symbols)  # Önceden seçilmiş sembolleri al, yoksa varsayılanları kullan

# Kullanıcıdan sembol ve tarih aralığını al
selected_symbols = st.multiselect("Select the symbols:", symbols, default=symbols)  # Seçilecek sembolleri çoklu seçim olarak sun
start_date = st.date_input("Enter the start date:", datetime(2024, 7, 27))  # Başlangıç tarihini kullanıcıdan al
end_date = st.date_input("Enter the end date:", datetime(2024, 7, 28))  # Bitiş tarihini kullanıcıdan al

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

interval_option = st.selectbox("Select the interval:", list(intervals.keys()))  # Zaman dilimi seçeneklerini sun
timeframe = intervals[interval_option]  # Kullanıcının seçtiği zaman dilimini belirle

# İndikatör seçimleri
indicators = st.multiselect("Select the indicators to display:", ["MA", "MACD", "RSI", "SMA", "EMA", "WMA"], default=["MA", "MACD", "RSI", "SMA", "EMA", "WMA"])  # Görüntülenecek indikatörleri seç

# Renk paleti tanımla
colors = ["blue", "red", "green", "orange", "purple"]

def get_next_color(colors, index):
    """Renk paletinden döngüsel olarak renk seç."""
    return colors[index % len(colors)]  # Renkleri döngüsel olarak seçer

# Verileri çekmek ve listelemek için buton
if st.button("Fetch Data"):  # Butona basıldığında veri çekme işlemi başlar
    fig_price = go.Figure()  # Fiyat grafiği için boş bir figür oluştur
    fig_macd = go.Figure()   # MACD grafiği için boş bir figür oluştur
    fig_rsi = go.Figure()    # RSI grafiği için boş bir figür oluştur

    all_data = []  # Tüm sembollerin verilerini saklayacak liste

    for symbol_index, symbol in enumerate(selected_symbols):  # Her sembol için döngü başlat
        # Tarihleri datetime formatına çevir
        utc_from = datetime.combine(start_date, datetime.min.time())  # Başlangıç tarihini datetime nesnesine dönüştür
        utc_to = datetime.combine(end_date, datetime.min.time())  # Bitiş tarihini datetime nesnesine dönüştür

        # Tarihsel verileri çek
        rates = mt5.copy_rates_range(symbol, timeframe, utc_from, utc_to)  # MetaTrader 5'ten tarihsel verileri çek

        if rates is None or len(rates) == 0:  # Eğer veri yoksa
            st.error(f"No data found for {symbol}")  # Hata mesajı göster
            continue  # Bir sonraki sembole geç

        # Verileri DataFrame'e dönüştür
        df = pd.DataFrame(rates)  # Verileri DataFrame'e çevir
        df['time'] = pd.to_datetime(df['time'], unit='s')  # Zaman bilgisini datetime formatına dönüştür
        df.set_index('time', inplace=True)  # Zamanı index olarak ayarla
        df = df[['open', 'high', 'low', 'close', 'tick_volume']]  # İlgili sütunları seç
        df['symbol'] = symbol  # Sembol bilgisini ekle
        df['interval'] = interval_option  # Interval bilgisini ekle

        # Verileri listeye ekle
        all_data.append(df)  # DataFrame'i veriler listesine ekle

        # Verileri PostgreSQL'e kaydet
        save_to_postgresql(df, interval_option)  # Verileri veritabanına kaydet

        # Mum çubukları grafiği
        fig_price.add_trace(go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name=f'{symbol} Candlestick'  # Grafiğin adı
        ))

        if "SMA" in indicators:  # Eğer SMA seçilmişse
            # SMA hesaplama (30 ve 50 günlük)
            df['SMA_30'] = df['close'].rolling(window=30).mean()  # 30 günlük SMA
            df['SMA_50'] = df['close'].rolling(window=50).mean()  # 50 günlük SMA

            # SMA çizgilerini grafiğe ekle
            fig_price.add_trace(go.Scatter(x=df.index, y=df['SMA_30'], mode='lines', name=f'{symbol} SMA 30', 
                line=dict(color=get_next_color(colors, symbol_index + 1))))
            fig_price.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], mode='lines', name=f'{symbol} SMA 50',
                line=dict(color=get_next_color(colors, symbol_index + 2))))

        if "EMA" in indicators:  # Eğer EMA seçilmişse
            # EMA hesaplama (12 ve 26 günlük)
            df['EMA_12'] = df['close'].ewm(span=12, adjust=False).mean()  # 12 günlük EMA
        
            df['EMA_26'] = df['close'].ewm(span=26, adjust=False).mean()  # 26 günlük EMA

            # EMA çizgilerini grafiğe ekle
            fig_price.add_trace(go.Scatter(x=df.index, y=df['EMA_12'], mode='lines', name=f'{symbol} EMA 12', 
                line=dict(color=get_next_color(colors, symbol_index + 3))))
            fig_price.add_trace(go.Scatter(x=df.index, y=df['EMA_26'], mode='lines', name=f'{symbol} EMA 26',
                line=dict(color=get_next_color(colors, symbol_index + 4))))

        if "WMA" in indicators:  # Eğer WMA seçilmişse
            # WMA hesaplama (14 ve 30 günlük)
            df['WMA_14'] = df['close'].rolling(window=14).apply(lambda x: (x * range(1, 15)).sum() / sum(range(1, 15)))  # 14 günlük WMA
            df['WMA_30'] = df['close'].rolling(window=30).apply(lambda x: (x * range(1, 31)).sum() / sum(range(1, 31)))  # 30 günlük WMA

            # WMA çizgilerini grafiğe ekle
            fig_price.add_trace(go.Scatter(x=df.index, y=df['WMA_14'], mode='lines', name=f'{symbol} WMA 14', 
                line=dict(color=get_next_color(colors, symbol_index + 5))))
            fig_price.add_trace(go.Scatter(x=df.index, y=df['WMA_30'], mode='lines', name=f'{symbol} WMA 30',
                line=dict(color=get_next_color(colors, symbol_index + 6))))

        if "MACD" in indicators:  # Eğer MACD seçilmişse
            # MACD hesaplama
            short_ema = df['close'].ewm(span=12, adjust=False).mean()  # Kısa vadeli üssel hareketli ortalama
            long_ema = df['close'].ewm(span=26, adjust=False).mean()  # Uzun vadeli üssel hareketli ortalama
            df['MACD'] = short_ema - long_ema  # MACD değerini hesapla
            df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()  # MACD sinyal çizgisi

            # MACD ve Signal Line grafikleri
            fig_macd.add_trace(go.Scatter(x=df.index, y=df['MACD'], mode='lines', name=f'{symbol} MACD',
                line=dict(color=get_next_color(colors, symbol_index))))
            fig_macd.add_trace(go.Scatter(x=df.index, y=df['Signal_Line'], mode='lines', name=f'{symbol} Signal Line',
                line=dict(color=get_next_color(colors, symbol_index + 1))))

        if "RSI" in indicators:  # Eğer RSI seçilmişse
            # RSI hesaplama
            delta = df['close'].diff()  # Fiyat değişimini hesapla
            gain = delta.where(delta > 0, 0)  # Pozitif değişimleri al
            loss = -delta.where(delta < 0, 0)  # Negatif değişimleri al
            avg_gain = gain.rolling(window=14).mean()  # Ortalama kazanç
            avg_loss = loss.rolling(window=14).mean()  # Ortalama kayıp

            rs = avg_gain / avg_loss  # Güçlülük Oranı
            df['RSI'] = 100 - (100 / (1 + rs))  # RSI hesapla

            # RSI grafiği
            fig_rsi.add_trace(go.Scatter(x=df.index, y=df['RSI'], mode='lines', name=f'{symbol} RSI',
                line=dict(color=get_next_color(colors, symbol_index))))

    # Grafikleri Streamlit'te göster
    st.plotly_chart(fig_price)  # Fiyat grafiğini göster
    st.plotly_chart(fig_macd)   # MACD grafiğini göster
    st.plotly_chart(fig_rsi)    # RSI grafiğini göster

    # Veritabanından verileri göster
    st.subheader("Data from PostgreSQL")  # Veritabanı verileri başlığı
    for symbol in selected_symbols:
        st.write(f"**{symbol}**")
        df_from_db = load_from_postgresql(symbol, interval_option)  # Veritabanından veri yükle
        st.dataframe(df_from_db)  # DataFrame'i göster

# MetaTrader 5 terminalini kapat
mt5.shutdown()