```markdown
# MT5 Data Fetcher and Technical Indicators

## Proje Açıklaması

MT5 Data Fetcher and Technical Indicators, MetaTrader 5 (MT5) kullanarak finansal piyasa verilerini
çeken ve bu verileri PostgreSQL veritabanına kaydeden bir uygulamadır. Ayrıca, kullanıcıların seçtiği
 teknik göstergelerle (MA, MACD, RSI) grafikler oluşturur ve bu grafikleri Streamlit kullanarak görüntüler.

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
```

### PostgreSQL Veritabanı Kurulumu

1. PostgreSQL veritabanını kurun.
2. `mt5_db` adında bir veritabanı oluşturun.
3. Aşağıdaki SQL komutunu kullanarak veritabanında gerekli tabloyu oluşturun:

```sql
CREATE TABLE mt5_db (
    time TIMESTAMP NOT NULL,
    open FLOAT NOT NULL,
    high FLOAT NOT NULL,
    low FLOAT NOT NULL,
    close FLOAT NOT NULL,
    tick_volume INTEGER NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    interval VARCHAR(20) NOT NULL,
    PRIMARY KEY (time, symbol, interval)
);
```

## Kullanım

1. MetaTrader 5 terminalini başlatın.
2. `streamlit run app.py` komutunu kullanarak uygulamayı başlatın.

   ```bash
   streamlit run app.py
   ```

3. Web tarayıcınızda açılan Streamlit uygulamasında aşağıdaki adımları izleyin:
   - Sembolleri seçin
   - Başlangıç ve bitiş tarihlerini girin
   - Zaman dilimi seçin
   - Görüntülenecek teknik göstergeleri seçin
   - "Fetch Data" butonuna tıklayın

## Kullanıcı Arayüzü

- **Sembol Seçimi:** Veri çekmek istediğiniz sembolleri seçin.
- **Tarih Aralığı:** Başlangıç ve bitiş tarihlerini belirleyin.
- **Zaman Dilimi:** Verilerin hangi zaman diliminde çekileceğini seçin.
- **İndikatörler:** MA, MACD ve RSI gibi teknik göstergeleri seçin.
- **Fetch Data Butonu:** Seçimlerinizi yapıp verileri çekmek için bu butona tıklayın.

## Katkıda Bulunma

Katkıda bulunmak isterseniz, lütfen bir pull request gönderin veya önerileriniz için iletişime geçin.

## Lisans

Bu proje MIT lisansı altında lisanslanmıştır. Daha fazla bilgi için [LICENSE](LICENSE) dosyasına bakın.

## İletişim

Herhangi bir soru veya öneriniz varsa, lütfen [mustafacangok@hotmail.com](mailto:mustafacangok@hotmail.com) adresi üzerinden benimle iletişime geçin.

```
