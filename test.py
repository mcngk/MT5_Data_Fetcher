import pandas as pd
import numpy as np
import plotly.graph_objs as go

def find_crossovers(series1, series2):
    """
    İki zaman serisi arasındaki kesişim noktalarını bulur.
    """
    diff = series1 - series2
    crossover_indices = np.where(np.diff(np.sign(diff)))[0] + 1
    return crossover_indices

def plot_ma20_ema12_crossovers(df):
    fig = go.Figure()

    # MA20 ve EMA12 hesaplama
    df['MA_20'] = df['close'].rolling(window=20).mean()
    df['EMA_12'] = df['close'].ewm(span=12, adjust=False).mean()

    # Kesişimleri bulma
    crossover_indices = find_crossovers(df['MA_20'].dropna(), df['EMA_12'].dropna())
    crossover_indices = crossover_indices.astype(int)
    crossover_times = df.index[df.index.isin(df['MA_20'].dropna().index[crossover_indices])]

    # Candlestick grafiği
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='Candlestick'
    ))

    # MA20 ve EMA12 çizgileri
    fig.add_trace(go.Scatter(x=df.index, y=df['MA_20'], mode='lines', name='MA 20',
        line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA_12'], mode='lines', name='EMA 12',
        line=dict(color='red')))

    # Kesişim noktaları
    fig.add_trace(go.Scatter(
        x=crossover_times,
        y=df['MA_20'].reindex(crossover_times),
        mode='markers',
        marker=dict(symbol='x', color='green', size=10),
        name='MA20/EMA12 Crossovers'
    ))

    fig.update_layout(title='MA20 and EMA12 Crossovers',
                      xaxis_title='Date',
                      yaxis_title='Price')
    return fig

# Örnek veri
df = pd.DataFrame({
    'time': pd.date_range(start='2023-01-01', periods=100),
    'open': np.random.rand(100) * 100,
    'high': np.random.rand(100) * 100,
    'low': np.random.rand(100) * 100,
    'close': np.random.rand(100) * 100,
})

df.set_index('time', inplace=True)

# Grafik oluşturma
fig = plot_ma20_ema12_crossovers(df)
fig.show()