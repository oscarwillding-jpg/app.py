import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
from datetime import datetime
from pycoingecko import CoinGeckoAPI

# ====================== INITIAL SETUP ======================
DATA_FILE = "assets_data.json"
UPLOAD_DIR = "uploaded_sources"
os.makedirs(UPLOAD_DIR, exist_ok=True)

cg = CoinGeckoAPI()

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"assets": {}}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()

st.set_page_config(page_title="My Asset Thesis Dashboard", layout="wide")
st.title("🧠 My Stocks & Cryptos Dashboard")

# ====================== SIDEBAR ======================
st.sidebar.header("Manage Assets")
new_ticker = st.sidebar.text_input("Add Asset (e.g. AAPL or BTC)", "").upper().strip()
asset_type = st.sidebar.selectbox("Type", ["Stock", "Crypto"])

if st.sidebar.button("➕ Add Asset"):
    if new_ticker and new_ticker not in data["assets"]:
        data["assets"][new_ticker] = {
            "type": asset_type,
            "thesis": "",
            "sources": [],
            "added": datetime.now().isoformat()
        }
        save_data(data)
        st.success(f"Added {new_ticker}")
    elif new_ticker:
        st.warning("Asset already exists")

# ====================== MAIN APP ======================
if not data["assets"]:
    st.info("👈 Add assets from the sidebar to get started.")
else:
    ticker = st.selectbox("Select Asset", list(data["assets"].keys()))
    asset = data["assets"][ticker]

    st.subheader(f"{ticker} — {asset['type']}")

    # ==================== CHARTS ====================
    st.subheader("📊 Price Charts")

    col_chart, col_info = st.columns([3, 1])

    with col_chart:
        timeframe = st.selectbox(
            "Timeframe",
            ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "max"],
            index=2
        )

        chart_type = st.radio("Chart Style", ["Candlestick + Indicators", "Simple Line"], horizontal=True)

        try:
            if asset["type"] == "Stock":
                stock = yf.Ticker(ticker)
                period_map = {"1d": "1d", "5d": "5d", "1mo": "1mo", "3mo": "3mo", 
                             "6mo": "6mo", "1y": "1y", "2y": "2y", "5y": "5y", "max": "max"}
                
                hist = stock.history(period=period_map[timeframe])

                if not hist.empty:
                    if chart_type == "Candlestick + Indicators":
                        fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                                            row_heights=[0.55, 0.25, 0.20], vertical_spacing=0.08)

                        # Candlestick
                        fig.add_trace(go.Candlestick(x=hist.index,
                            open=hist['Open'], high=hist['High'],
                            low=hist['Low'], close=hist['Close'], name="OHLC"), row=1, col=1)

                        # Moving Averages
                        hist['SMA50'] = hist['Close'].rolling(50).mean()
                        hist['SMA200'] = hist['Close'].rolling(200).mean()
                        fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA50'], name="SMA 50", line=dict(color='orange')), row=1, col=1)
                        fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA200'], name="SMA 200", line=dict(color='red')), row=1, col=1)

                        # Volume
                        fig.add_trace(go.Bar(x=hist.index, y=hist['Volume'], name="Volume", marker_color='rgba(0,150,255,0.6)'), row=2, col=1)

                        # RSI
                        delta = hist['Close'].diff()
                        gain = delta.where(delta > 0, 0).rolling(14).mean()
                        loss = -delta.where(delta < 0, 0).rolling(14).mean()
                        rs = gain / loss
                        rsi = 100 - (100 / (1 + rs))
                        fig.add_trace(go.Scatter(x=hist.index, y=rsi, name="RSI (14)", line=dict(color='purple')), row=3, col=1)
                        fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
                        fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)

                        fig.update_layout(height=700, title=f"{ticker} - Technical Analysis")
                        fig.update_xaxes(rangeslider_visible=False)

                    else:  # Simple Line
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], name="Close Price"))
                        fig.update_layout(title=f"{ticker} Price History", height=500)

                    st.plotly_chart(fig, use_container_width=True)

                    # Current Price
                    current = hist['Close'][-1]
                    change = ((current - hist['Close'][-2]) / hist['Close'][-2]) * 100 if len(hist) > 1 else 0
                    st.metric("Latest Price", f"${current:.2f}", f"{change:+.2f}%")

            else:  # Crypto
                coins = cg.get_coins_list()
                coin_id = next((coin['id'] for coin in coins if coin['symbol'].upper() == ticker), None)

                if coin_id:
                    days_map = {"1d":1, "5d":5, "1mo":30, "3mo":90, "6mo":180, "1y":365, "2y":730, "5y":1825, "max":"max"}
                    market_data = cg.get_coin_market_chart_by_id(coin_id, vs_currency='usd', days=days_map[timeframe])

                    df_price = pd.DataFrame(market_data['prices'], columns=['timestamp', 'price'])
                    df_price['date'] = pd.to_datetime(df_price['timestamp'], unit='ms')

                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=df_price['date'], y=df_price['price'], name="Price"))
                    fig.update_layout(title=f"{ticker} Price Chart", height=550)
                    st.plotly_chart(fig, use_container_width=True)

                    price_now = df_price['price'].iloc[-1]
                    st.metric("Current Price", f"${price_now:,.4f}")

        except Exception as e:
            st.error(f"Could not load chart data: {e}")

    # ==================== THESIS ====================
    st.subheader("📝 My Thesis / Opinion")
    thesis = st.text_area("Write your investment thesis, risks, catalysts, etc.", 
                         asset.get("thesis", ""), height=300)
    if st.button("💾 Save Thesis"):
        data["assets"][ticker]["thesis"] = thesis
        save_data(data)
        st.success("Thesis saved successfully!")

    # ==================== SOURCES ====================
    st.subheader("🔗 Sources & Macro Influences")

    c1, c2 = st.columns(2)
    with c1:
        src_name = st.text_input("Source Title/Name")
        src_url = st.text_input("Link / URL")
    with c2:
        uploaded_file = st.file_uploader("Upload file (PDF, image, etc.)", type=["pdf","png","jpg","jpeg","csv","txt"])

    if st.button("Add Source"):
        new_src = {"name": src_name or "Untitled Source", "url": src_url, "date": datetime.now().isoformat()}
        if uploaded_file:
            file_path = os.path.join(UPLOAD_DIR, f"{ticker}_{datetime.now().strftime('%Y%m%d_%H%M')}_{uploaded_file.name}")
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            new_src["file_path"] = file_path
        asset["sources"].append(new_src)
        save_data(data)
        st.rerun()

    # Display sources
    if asset.get("sources"):
        st.write("**Saved Sources:**")
        for i, src in enumerate(reversed(asset["sources"])):
            with st.expander(f"{src['name']} — {src.get('date','')[:10]}"):
                if src.get("url"):
                    st.markdown(f"🔗 [Open Link]({src['url']})")
                if src.get("file_path") and os.path.exists(src["file_path"]):
                    st.download_button("📥 Download File", 
                                     data=open(src["file_path"], "rb").read(),
                                     file_name=os.path.basename(src["file_path"]),
                                     key=f"dl{i}")
    else:
        st.caption("No sources added yet.")

st.sidebar.info("✅ Dashboard is running locally or on Streamlit Cloud")
