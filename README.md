# MT5 Data Fetcher and Technical Indicators

## Proje Açıklaması

MT5 Data Fetcher and Technical Indicators, MetaTrader 5 (MT5) kullanarak finansal piyasa verileriniçeken ve bu verileri PostgreSQL
veritabanına kaydeden bir uygulamadır. Ayrıca, kullanıcıların seçtiği teknik göstergelerle (MA, MACD, RSI) grafikler oluşturur ve
bu grafikleri Streamlit kullanarak görüntüler.

## Özellikler

- MetaTrader 5 ile bağlantı kurarak tarihsel piyasa verilerini çekme
- Verileri PostgreSQL veritabanına kaydetme
- Kullanıcıların belirlediği teknik göstergelerle grafikler oluşturma
- Streamlit arayüzü ile grafiklerin görselleştirilmesi

## Kurulum

### Gereksinimler

- Python 3.12.1
- MetaTrader 5 terminali
- PostgreSQL 14 veritabanı
- İlgili Python kütüphaneleri

### Kütüphaneler

Projenin ihtiyaç duyduğu kütüphaneleri yüklemek için:

```bash
pip install MetaTrader5 pandas psycopg2 streamlit plotly
