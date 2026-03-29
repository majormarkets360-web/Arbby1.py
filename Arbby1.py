# app.py - Simplified version without TensorFlow
import streamlit as st
import asyncio
import aiohttp
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import time
from collections import defaultdict
import requests
from web3 import Web3
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import MinMaxScaler
from sklearn.linear_model import LinearRegression
import joblib
import warnings
warnings.filterwarnings('ignore')

# Page config
st.set_page_config(
    page_title="AI Crypto Arbitrage Scanner",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stAlert {
        position: fixed;
        top: 10px;
        right: 10px;
        z-index: 999;
    }
    .ad-placeholder {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        text-align: center;
        color: white;
        border: 2px solid rgba(255,255,255,0.2);
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.02); }
        100% { transform: scale(1); }
    }
    .profit-positive {
        color: #00ff00;
        font-weight: bold;
    }
    .metric-card {
        background: rgba(255,255,255,0.1);
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'arbitrage_opportunities' not in st.session_state:
    st.session_state.arbitrage_opportunities = []
if 'price_history' not in st.session_state:
    st.session_state.price_history = defaultdict(list)
if 'alert_queue' not in st.session_state:
    st.session_state.alert_queue = []
if 'streaming_active' not in st.session_state:
    st.session_state.streaming_active = False

class CryptoDataFetcher:
    """Handles real-time crypto data fetching"""
    
    def __init__(self):
        self.exchanges = {
            'binance': 'https://api.binance.com/api/v3',
            'coinbase': 'https://api.coinbase.com/v2',
            'kraken': 'https://api.kraken.com/0/public',
            'bybit': 'https://api.bybit.com/v5'
        }
        
    async def fetch_token_price(self, token_symbol, exchange):
        """Fetch current price from specific exchange"""
        async with aiohttp.ClientSession() as session:
            try:
                if exchange == 'binance':
                    url = f"{self.exchanges['binance']}/ticker/price?symbol={token_symbol}USDT"
                    async with session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            return float(data['price'])
                        else:
                            return None
                elif exchange == 'coinbase':
                    url = f"{self.exchanges['coinbase']}/prices/{token_symbol}-USD/spot"
                    async with session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            return float(data['data']['amount'])
                        else:
                            return None
                elif exchange == 'kraken':
                    url = f"{self.exchanges['kraken']}/ticker?pair={token_symbol}USD"
                    async with session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            result = data.get('result', {})
                            if result:
                                pair_key = list(result.keys())[0]
                                return float(result[pair_key]['c'][0])
                        return None
                else:
                    return None
            except Exception as e:
                # Silently fail for individual exchange errors
                return None

class AIPricePredictor:
    """Simplified AI model for price predictions using scikit-learn"""
    
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=50, random_state=42)
        self.scaler = MinMaxScaler()
        self.is_trained = False
        
    def prepare_features(self, prices):
        """Prepare features for prediction"""
        if len(prices) < 10:
            return None
        
        # Create features: moving averages, volatility, momentum
        features = []
        targets = []
        
        for i in range(10, len(prices) - 1):
            # Features
            recent_prices = prices[i-10:i]
            ma_5 = np.mean(recent_prices[-5:])
            ma_10 = np.mean(recent_prices)
            volatility = np.std(recent_prices)
            momentum = recent_prices[-1] - recent_prices[0]
            
            features.append([ma_5, ma_10, volatility, momentum, prices[i-1]])
            targets.append(prices[i])
        
        return np.array(features), np.array(targets)
    
    def predict_price(self, historical_prices, days_ahead=1):
        """Predict future price based on historical data"""
        if len(historical_prices) < 20:
            return np.array([historical_prices[-1] if historical_prices else 0] * days_ahead)
        
        # Prepare features
        features, targets = self.prepare_features(historical_prices)
        
        if features is not None and len(features) > 10:
            # Train model on available data
            self.model.fit(features, targets)
            self.is_trained = True
            
            # Make predictions
            predictions = []
            current_features = features[-1:]
            
            for _ in range(days_ahead):
                pred = self.model.predict(current_features)[0]
                predictions.append(pred)
                
                # Update features for next prediction
                last_price = pred
                current_features = np.roll(current_features, -1)
                current_features[0][-1] = last_price
            
            return np.array(predictions)
        else:
            # Fallback to simple moving average
            return np.array([np.mean(historical_prices[-5:])] * days_ahead)
    
    def generate_signal(self, current_price, predicted_price, volatility):
        """Generate buy/sell/hold signal"""
        if predicted_price is None or current_price == 0:
            return "HOLD", "Insufficient data"
        
        price_change = ((predicted_price - current_price) / current_price) * 100
        
        if price_change > 3 and volatility < 30:
            return "STRONG_BUY", f"High upside potential: {price_change:.1f}% expected increase"
        elif price_change > 1:
            return "BUY", f"Positive movement expected: {price_change:.1f}%"
        elif price_change < -3 and volatility > 50:
            return "STRONG_SELL", f"High downside risk: {price_change:.1f}% expected decrease"
        elif price_change < -1:
            return "SELL", f"Negative movement expected: {price_change:.1f}%"
        else:
            return "HOLD", f"Neutral conditions with {price_change:.1f}% expected change"

class ArbitrageScanner:
    """Main arbitrage opportunity scanner"""
    
    def __init__(self, data_fetcher, ai_predictor):
        self.data_fetcher = data_fetcher
        self.ai_predictor = ai_predictor
        self.min_profit_threshold = 0.5
        
    async def find_opportunities(self, tokens):
        """Find arbitrage opportunities"""
        opportunities = []
        
        for token in tokens:
            prices = {}
            
            # Fetch prices from all exchanges
            for exchange in self.data_fetcher.exchanges.keys():
                price = await self.data_fetcher.fetch_token_price(token, exchange)
                if price:
                    prices[exchange] = price
            
            # Find price differences
            if len(prices) >= 2:
                max_price = max(prices.values())
                min_price = min(prices.values())
                spread = ((max_price - min_price) / min_price) * 100
                
                if spread >= self.min_profit_threshold:
                    buy_exchange = min(prices, key=prices.get)
                    sell_exchange = max(prices, key=prices.get)
                    
                    # Calculate profit margin after fees (assuming 0.1% fee)
                    profit_margin = spread - 0.2
                    
                    # Get volatility and confidence
                    historical = st.session_state.price_history.get(token, [])
                    volatility = np.std(historical[-20:]) / np.mean(historical[-20:]) if len(historical) >= 20 else 0.5
                    confidence = min(0.95, max(0.3, spread / (volatility * 100))) if volatility > 0 else 0.5
                    
                    opportunities.append({
                        'token': token,
                        'buy_exchange': buy_exchange,
                        'sell_exchange': sell_exchange,
                        'buy_price': prices[buy_exchange],
                        'sell_price': prices[sell_exchange],
                        'profit_margin': profit_margin,
                        'timestamp': datetime.now(),
                        'confidence': confidence,
                        'spread': spread
                    })
        
        return sorted(opportunities, key=lambda x: x['profit_margin'], reverse=True)

# Initialize components
data_fetcher = CryptoDataFetcher()
ai_predictor = AIPricePredictor()
scanner = ArbitrageScanner(data_fetcher, ai_predictor)

# Main UI
st.title("🤖 AI Crypto Arbitrage Scanner")
st.markdown("---")

# Create sidebar
with st.sidebar:
    st.header("🎮 Controls")
    
    # Token selection
    default_tokens = ["BTC", "ETH", "BNB", "SOL", "ADA", "DOGE"]
    selected_tokens = st.multiselect(
        "Select Tokens to Monitor",
        default_tokens,
        default=["BTC", "ETH"]
    )
    
    # Scan settings
    scan_interval = st.slider("Scan Interval (seconds)", 2, 30, 10)
    min_profit = st.slider("Minimum Profit Threshold (%)", 0.1, 5.0, 0.5)
    scanner.min_profit_threshold = min_profit
    
    # Start/Stop scanning
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 Start Scanning", type="primary", use_container_width=True):
            st.session_state.scanning = True
    with col2:
        if st.button("⏹️ Stop Scanning", use_container_width=True):
            st.session_state.scanning = False
    
    st.markdown("---")
    st.info("💡 **Tip**: Add more tokens for broader coverage. Lower profit threshold for more opportunities.")

# Main content - 2 columns
col_main, col_ads = st.columns([3, 1])

with col_main:
    # Status indicator
    if st.session_state.get('scanning', False):
        st.success("🟢 Scanner Active - Real-time monitoring in progress")
    else:
        st.warning("⚪ Scanner Stopped - Click 'Start Scanning' to begin")
    
    # Live metrics
    st.header("📊 Live Market Metrics")
    metric_cols = st.columns(4)
    
    with metric_cols[0]:
        st.metric("Opportunities Found", len(st.session_state.arbitrage_opportunities))
    with metric_cols[1]:
        avg_profit = np.mean([opp['profit_margin'] for opp in st.session_state.arbitrage_opportunities]) if st.session_state.arbitrage_opportunities else 0
        st.metric("Avg Profit Margin", f"{avg_profit:.2f}%")
    with metric_cols[2]:
        high_conf = len([opp for opp in st.session_state.arbitrage_opportunities if opp.get('confidence', 0) > 0.7])
        st.metric("High Confidence", high_conf)
    with metric_cols[3]:
        st.metric("Status", "🟢 Active" if st.session_state.get('scanning', False) else "⭕ Stopped")
    
    # Arbitrage opportunities
    st.header("🎯 Arbitrage Opportunities")
    
    if st.session_state.arbitrage_opportunities:
        df = pd.DataFrame(st.session_state.arbitrage_opportunities)
        df['profit_margin'] = df['profit_margin'].apply(lambda x: f"{x:.2f}%")
        df['confidence'] = df['confidence'].apply(lambda x: f"{x:.1%}")
        df['timestamp'] = df['timestamp'].dt.strftime("%H:%M:%S")
        
        display_df = df[['token', 'buy_exchange', 'sell_exchange', 'profit_margin', 'confidence', 'timestamp']]
        st.dataframe(display_df, use_container_width=True)
        
        # Show top opportunity
        if st.session_state.arbitrage_opportunities:
            top_opp = st.session_state.arbitrage_opportunities[0]
            st.success(f"🏆 **Top Opportunity**: {top_opp['token']} - {top_opp['profit_margin']:.2f}% profit buying on {top_opp['buy_exchange']} and selling on {top_opp['sell_exchange']}")
    else:
        st.info("No arbitrage opportunities found. Waiting for price discrepancies...")
    
    # AI Predictions
    st.header("🔮 AI Price Predictions")
    
    for token in selected_tokens:
        with st.expander(f"📈 {token} Analysis"):
            historical = st.session_state.price_history.get(token, [])
            
            if len(historical) >= 10:
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    # Price chart
                    fig = go.Figure()
                    
                    # Historical prices
                    fig.add_trace(go.Scatter(
                        y=historical[-50:],
                        mode='lines',
                        name='Historical',
                        line=dict(color='blue', width=2)
                    ))
                    
                    # Add prediction
                    predictions = ai_predictor.predict_price(historical, 5)
                    future_x = list(range(len(historical[-50:]), len(historical[-50:]) + len(predictions)))
                    fig.add_trace(go.Scatter(
                        x=future_x,
                        y=predictions,
                        mode='lines+markers',
                        name='AI Prediction',
                        line=dict(color='red', width=2, dash='dash'),
                        marker=dict(size=8)
                    ))
                    
                    fig.update_layout(
                        title=f"{token} Price Chart with AI Prediction",
                        xaxis_title="Time Steps",
                        yaxis_title="Price (USD)",
                        height=350,
                        hovermode='x unified'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    current_price = historical[-1]
                    predicted_price = predictions[0] if len(predictions) > 0 else current_price
                    volatility = np.std(historical[-20:]) / np.mean(historical[-20:]) if len(historical) >= 20 else 0.5
                    
                    signal, reason = ai_predictor.generate_signal(current_price, predicted_price, volatility)
                    
                    st.metric("Current Price", f"${current_price:,.2f}")
                    st.metric("Predicted Price (Next)", f"${predicted_price:,.2f}", 
                             delta=f"{((predicted_price - current_price)/current_price*100):.1f}%")
                    
                    signal_color = "🟢" if "BUY" in signal else "🔴" if "SELL" in signal else "🟡"
                    st.markdown(f"### {signal_color} {signal}")
                    st.caption(reason)
                    
                    # Confidence meter
                    confidence_score = min(1.0, max(0.3, 1 - volatility))
                    st.progress(confidence_score)
                    st.caption(f"Prediction Confidence: {confidence_score:.0%}")
            else:
                st.info(f"📊 Collecting price history for {token}... Need {10 - len(historical)} more data points")
    
    # Alerts
    st.header("⚠️ Recent Alerts")
    alert_container = st.container()
    
    with alert_container:
        if st.session_state.alert_queue:
            for alert in st.session_state.alert_queue[-5:]:
                st.warning(alert)
        else:
            st.info("No alerts yet. High-profit opportunities will appear here.")

with col_ads:
    st.header("📢 Sponsors")
    
    # 5 advertisement placeholders with different content
    ads = [
        {"title": "🚀 Trade Smarter", "content": "Advanced trading tools & analytics", "link": "#"},
        {"title": "🔒 Secure Wallet", "content": "Store your crypto safely", "link": "#"},
        {"title": "📚 Learn Trading", "content": "Master crypto trading strategies", "link": "#"},
        {"title": "💎 DeFi Insights", "content": "Latest DeFi opportunities", "link": "#"},
        {"title": "⚡ Mining Pool", "content": "Join the largest mining pool", "link": "#"}
    ]
    
    for i, ad in enumerate(ads, 1):
        with st.container():
            st.markdown(f"""
            <div class="ad-placeholder">
                <h3>{ad['title']}</h3>
                <p>{ad['content']}</p>
                <small>Advertisement {i}</small>
            </div>
            """, unsafe_allow_html=True)

# Background scanning logic
async def continuous_scan():
    """Continuous scanning function"""
    while st.session_state.get('scanning', False):
        if selected_tokens:
            opportunities = await scanner.find_opportunities(selected_tokens)
            st.session_state.arbitrage_opportunities = opportunities[:20]
            
            # Generate alerts for high-profit opportunities
            for opp in opportunities:
                if opp['profit_margin'] > min_profit * 2:
                    alert = f"🚨 ALERT: {opp['token']} - {opp['profit_margin']:.2f}% profit! Buy: {opp['buy_exchange']} → Sell: {opp['sell_exchange']}"
                    if alert not in st.session_state.alert_queue[-5:]:
                        st.session_state.alert_queue.append(alert)
                        if len(st.session_state.alert_queue) > 10:
                            st.session_state.alert_queue.pop(0)
            
            # Update price history
            for token in selected_tokens:
                price = await data_fetcher.fetch_token_price(token, 'binance')
                if price:
                    st.session_state.price_history[token].append(price)
                    # Keep last 200 data points
                    if len(st.session_state.price_history[token]) > 200:
                        st.session_state.price_history[token] = st.session_state.price_history[token][-200:]
        
        await asyncio.sleep(scan_interval)

# Run background scanning (simplified for Streamlit)
def start_scanning():
    if st.session_state.get('scanning', False):
        # Simple loop without complex asyncio for Streamlit
        import threading
        def run_scan():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(continuous_scan())
        
        thread = threading.Thread(target=run_scan, daemon=True)
        thread.start()

# Auto-start if scanning is enabled
if st.session_state.get('scanning', False):
    start_scanning()

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center">
    <small>🤖 AI-Powered Crypto Arbitrage Scanner | Real-time Monitoring | 5+ Exchanges Supported</small><br>
    <small>Data refreshes every few seconds | Predictions based on machine learning</small>
</div>
""", unsafe_allow_html=True)
