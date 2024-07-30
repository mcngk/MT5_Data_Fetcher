#veri işleme, model yükleme ve görselleştirme işlemleri için gerekli kütüphaneleri içe aktarılması

import streamlit as st
import pandas as pd
import numpy as np
from keras.models import load_model
import matplotlib.pyplot as plt
import yfinance as yf

st.title("Stock Price Predictor App")

# PAGE LAYOUT
stock_symbol, selected_time, selected_indicator = st.columns((1, 1, 1))

# SYMBOL INPUT
with stock_symbol:
    stock = st.text_input('Enter a stock',"TSLA")
    stock = stock.upper()

# PREDICT NUMBER OF DAYS OUT
with selected_time:
    selected_time = st.selectbox("Time Select", ("5 min","15 min","30 min"))

# # PREDICT NUMBER OF DAYS OUT
# with forecast_column:
#     forecastDays = st.number_input(label = 'Forecast Days...', step=1)
#     if forecastDays < 0:
#         st.write('ERROR: Number must be positive')

with selected_indicator:
    selected_indicator = st.selectbox("Indicator Select", ("MA","RSI","MACD"))
    

#Streamlit uygulamanızda kullanıcıdan bir hisse senedi sembolü girmesini sağlayan bir giriş alanı oluşturur.

from datetime import date, datetime
end = datetime.now()
start = datetime(end.year-1,end.month,end.day)

data = yf.download(stock, start, end, interval= "5m")

model = load_model("Latest_stock_price_model.keras")
st.subheader("Stock Price Data")
st.write(data)

splitting_len = int(len(data)*0.7)
x_test = pd.DataFrame(data.Close[splitting_len:])

#Veri setinin %70'ini eğitim verisi olarak ayırmak için bir indeks hesaplar.
#Kalan %30'luk kısmı test verisi olarak kullanılacaktır.

def plot_graph(figsize, values, full_data, extra_data = 0, extra_dataset = None):
    fig = plt.figure(figsize=figsize)
    plt.plot(values,'Red')
    plt.plot(full_data.Close, 'b')
    if extra_data:
        plt.plot(extra_dataset)
    return fig
if selected_indicator == "MA":
    st.subheader('Original Close Price and MA for 250 days')
    data['MA_for_250_days'] = data.Close.rolling(250).mean()
    st.pyplot(plot_graph((16,7), data['MA_for_250_days'],data))
    plt.xlabel(["Original Close Price", "MA for 250 days"])

    st.subheader('Original Close Price and MA for 100 days')
    data['MA_for_100_days'] = data.Close.rolling(100).mean()
    st.pyplot(plot_graph((16,7), data['MA_for_100_days'],data))

    st.subheader('Original Close Price and MA for 100 days and MA for 250 days')
    st.pyplot(plot_graph((16,7), data['MA_for_100_days'],data,1,data['MA_for_250_days']))

    from sklearn.preprocessing import MinMaxScaler

    scaler = MinMaxScaler(feature_range=(0,1))
    scaled_data = scaler.fit_transform(x_test[['Close']])

    x_data = []
    y_data = []

    for i in range(100,len(scaled_data)):
        x_data.append(scaled_data[i-100:i])
        y_data.append(scaled_data[i])

    x_data, y_data = np.array(x_data), np.array(y_data)

    predictions = model.predict(x_data)

    inv_pre = scaler.inverse_transform(predictions)
    inv_y_test = scaler.inverse_transform(y_data)

    ploting_data = pd.DataFrame(
    {
        'original_test_data': inv_y_test.reshape(-1),
        'predictions': inv_pre.reshape(-1)
    } ,
        index = data.index[splitting_len+100:]
    )

    st.subheader("Original values vs Predicted values")

    st.write(ploting_data)

    st.subheader('Original Close Price vs Predicted Close price')
    fig = plt.figure(figsize=(16,7))
    plt.plot(pd.concat([data.Close[:splitting_len+100],ploting_data], axis=0))
    plt.legend(["Data- not used", "Original Test data", "Predicted Test data"])
    st.pyplot(fig)

# def show_prices(forecastDays, stock):
#     if forecastDays < 0 or forecastDays == 0:
#         st.write('[ERROR]: CHECK NUMBER INPUT')
#     else:
#         # GET STOCK NAMES
#         stock_df = stock()
#         if stock not in stock.index:
#             no_data = st.write('Not a valid stock')
#             return no_data
#         else:
#             pred = model(forecastDays, stock)

#             col_vals = [f'Stock Price Prediction for {stock}']

#             pred_df = pd.DataFrame(
#                 data = pred,
#                 columns = col_vals
#             )

#             # pred_df = pred_df.apply(lambda x: round(x, 2))


#             return pred_df


# stock_price_show, stock_dis = st.columns((1, 1))

# with stock_price_show:
#     if forecastDays < 0 or forecastDays == 0:
#         st.write('[ERROR]: CHECK NUMBER INPUT')
#     else:
#         # GET STOCK NAMES
#         stock_df = stock()
#         if stock not in stock_df.index:
#             st.write('Not a valid stock')
#         else:
#             STOCK_PRICE_DF = show_prices(forecastDays, stock)
#             s = [f'Stock Price Prediction for {stock}']
#             st.write(f'Showing Stock Prices up to: {date.today() + datetime. timedelta(days=forecastDays)}')
#             for i in range(len(STOCK_PRICE_DF)):
#                 st.write(f'${round(STOCK_PRICE_DF.iloc[i, 0], 2)} --- [DAY: {i + 1}]')
#     st.write(show_prices(forecastDays, stock))