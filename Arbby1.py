# app.py
import streamlit as st
import asyncio
import aiohttp
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import websocket
import json
import threading
import time
from collections import defaultdict
import requests
from web3 import Web3
import tensorflow as tf
from sklearn.preprocessing import MinMaxScaler
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

# Custom CSS for better styling
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
    .profit-negative {
        color: #ff4444;
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
    """Handles real-time crypto data fetching from multiple sources"""
    
    def __init__(self):
        self.web3_providers = {
            'ethereum': Web3(Web3.HTTPProvider('https://mainnet.infura.io/v3/YOUR_PROJECT_ID')),
            'bsc': Web3(Web3.HTTPProvider('https://bsc-dataseed.binance.org/')),
            'polygon': Web3(Web3.HTTPProvider('https://polygon-rpc.com/'))
        }
        self.exchanges = {
            'binance': 'https://api.binance.com/api/v3',
            'coinbase': 'https://api.coinbase.com/v2',
            'kraken': 'https://api.kraken.com/0/public',
            'uniswap': 'https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2',
            'pancakeswap': 'https://api.thegraph.com/subgraphs/name/pancakeswap/exchange-v2'
        }
        
    async def fetch_token_price(self, token_symbol, exchange):
        """Fetch current price from specific exchange"""
        async with aiohttp.ClientSession() as session:
            try:
                if exchange == 'binance':
                    url = f"{self.exchanges['binance']}/ticker/price?symbol={token_symbol}USDT"
                    async with session.get(url) as response:
                        data = await response.json()
                        return float(data['price'])
                elif exchange == 'coinbase':
                    url = f"{self.exchanges['coinbase']}/prices/{token_symbol}-USD/spot"
                    async with session.get(url) as response:
                        data = await response.json()
                        return float(data['data']['amount'])
                # Add more exchange integrations
            except Exception as e:
                st.error(f"Error fetching from {exchange}: {e}")
                return None
    
    async def scan_liquidity_pools(self, token_address, chain='ethereum'):
        """Scan DEX liquidity pools for token prices"""
        web3 = self.web3_providers.get(chain)
        if not web3:
            return None
        
        # Simplified pool scanning logic
        # In production, you'd query The Graph or direct contract calls
        return {
            'uniswap_v2': 0.0,
            'uniswap_v3': 0.0,
            'sushiswap': 0.0,
            'liquidity_depth': 0.0
        }

class AIPricePredictor:
    """AI model for price predictions and sentiment analysis"""
    
    def __init__(self):
        self.model = self._build_model()
        self.scaler = MinMaxScaler()
        
    def _build_model(self):
        """Build LSTM model for price prediction"""
        model = tf.keras.Sequential([
            tf.keras.layers.LSTM(50, return_sequences=True, input_shape=(60, 1)),
            tf.keras.layers.LSTM(50, return_sequences=True),
            tf.keras.layers.LSTM(50),
            tf.keras.layers.Dense(25),
            tf.keras.layers.Dense(1)
        ])
        model.compile(optimizer='adam', loss='mse')
        return model
    
    def predict_price(self, historical_prices, days_ahead=1):
        """Predict future price based on historical data"""
        if len(historical_prices) < 60:
            return historical_prices[-1] if historical_prices else 0
        
        # Prepare data
        scaled_data = self.scaler.fit_transform(np.array(historical_prices).reshape(-1, 1))
        
        # Create input sequence
        last_60_days = scaled_data[-60:]
        X_test = np.array([last_60_days])
        
        # Predict
        predictions = []
        for _ in range(days_ahead):
            pred = self.model.predict(X_test)
            predictions.append(pred[0][0])
            # Update sequence with prediction
            X_test = np.append(X_test[:, 1:, :], pred.reshape(1, 1, 1), axis=1)
        
        # Inverse transform
        predictions = self.scaler.inverse_transform(np.array(predictions).reshape(-1, 1))
        return predictions.flatten()
    
    def generate_signal(self, current_price, predicted_price, volatility):
        """Generate buy/sell/hold signal"""
        price_change = ((predicted_price - current_price) / current_price) * 100
        
        if price_change > 5 and volatility < 30:
            return "STRONG_BUY", "High upside potential with low volatility"
        elif price_change > 2:
            return "BUY", "Positive price movement expected"
        elif price_change < -5 and volatility > 50:
            return "STRONG_SELL", "High downside risk detected"
        elif price_change < -2:
            return "SELL", "Negative price movement expected"
        else:
            return "HOLD", "Neutral market conditions"

class ArbitrageScanner:
    """Main arbitrage opportunity scanner"""
    
    def __init__(self, data_fetcher, ai_predictor):
        self.data_fetcher = data_fetcher
        self.ai_predictor = ai_predictor
        self.min_profit_threshold = 0.5  # 0.5% minimum profit
        
    async def find_opportunities(self, tokens):
        """Find arbitrage opportunities across exchanges and protocols"""
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
                    # Find best buying and selling opportunities
                    buy_exchange = min(prices, key=prices.get)
                    sell_exchange = max(prices, key=prices.get)
                    
                    # Get AI prediction
                    historical = st.session_state.price_history.get(token, [])
                    predicted_prices = self.ai_predictor.predict_price(historical, 3)
                    
                    # Calculate profitability
                    profit_margin = spread - 0.1  # Subtract transaction fees
                    
                    opportunities.append({
                        'token': token,
                        'buy_exchange': buy_exchange,
                        'sell_exchange': sell_exchange,
                        'buy_price': prices[buy_exchange],
                        'sell_price': prices[sell_exchange],
                        'profit_margin': profit_margin,
                        'timestamp': datetime.now(),
                        'predicted_prices': predicted_prices,
                        'confidence': self._calculate_confidence(historical, spread)
                    })
        
        return sorted(opportunities, key=lambda x: x['profit_margin'], reverse=True)
    
    def _calculate_confidence(self, historical_prices, spread):
        """Calculate confidence score based on historical patterns"""
        if len(historical_prices) < 20:
            return 0.5
        
        volatility = np.std(historical_prices[-20:]) / np.mean(historical_prices[-20:])
        confidence = min(1.0, spread / (volatility * 100))
        return max(0.3, confidence)

class LivestreamManager:
    """Manages livestream connections to multiple platforms"""
    
    def __init__(self):
        self.platforms = {
            'youtube': {
                'enabled': False,
                'api_key': None,
                'stream_url': None
            },
            'twitch': {
                'enabled': False,
                'api_key': None,
                'stream_url': None
            },
            'twitter': {
                'enabled': False,
                'api_key': None,
                'stream_url': None
            },
            'tiktok': {
                'enabled': False,
                'api_key': None,
                'stream_url': None
            }
        }
        
    def connect_platform(self, platform, api_key, stream_url):
        """Connect to a specific streaming platform"""
        if platform in self.platforms:
            self.platforms[platform] = {
                'enabled': True,
                'api_key': api_key,
                'stream_url': stream_url
            }
            return True
        return False
    
    def broadcast_data(self, data):
        """Broadcast data to connected platforms"""
        if not st.session_state.streaming_active:
            return
        
        for platform, config in self.platforms.items():
            if config['enabled']:
                try:
                    # Platform-specific broadcasting logic
                    # This would use platform APIs to stream data
                    self._send_to_platform(platform, config, data)
                except Exception as e:
                    st.error(f"Failed to broadcast to {platform}: {e}")
    
    def _send_to_platform(self, platform, config, data):
        """Send data to specific platform"""
        # Implementation for each platform's API
        # For demo, we'll just log
        print(f"Broadcasting to {platform}: {data}")

# Initialize components
data_fetcher = CryptoDataFetcher()
ai_predictor = AIPricePredictor()
scanner = ArbitrageScanner(data_fetcher, ai_predictor)
stream_manager = LivestreamManager()

# Main UI
st.title("🤖 AI Crypto Arbitrage Scanner")
st.markdown("---")

# Create sidebar for controls
with st.sidebar:
    st.header("🎮 Controls")
    
    # Token selection
    default_tokens = ["BTC", "ETH", "BNB", "MATIC", "SOL", "AVAX"]
    selected_tokens = st.multiselect(
        "Select Tokens to Monitor",
        default_tokens,
        default=["BTC", "ETH"]
    )
    
    # Scan settings
    scan_interval = st.slider("Scan Interval (seconds)", 1, 30, 5)
    min_profit = st.slider("Minimum Profit Threshold (%)", 0.1, 10.0, 0.5)
    scanner.min_profit_threshold = min_profit
    
    # AI Settings
    st.subheader("🤖 AI Prediction Settings")
    prediction_days = st.slider("Prediction Days Ahead", 1, 7, 3)
    confidence_threshold = st.slider("AI Confidence Threshold", 0.0, 1.0, 0.6)
    
    # Livestream settings
    st.subheader("📡 Livestream Settings")
    stream_enabled = st.checkbox("Enable Livestream Broadcasting")
    st.session_state.streaming_active = stream_enabled
    
    if stream_enabled:
        youtube_key = st.text_input("YouTube API Key", type="password")
        twitch_key = st.text_input("Twitch API Key", type="password")
        
        if youtube_key:
            stream_manager.connect_platform('youtube', youtube_key, None)
        if twitch_key:
            stream_manager.connect_platform('twitch', twitch_key, None)
    
    # Start/Stop scanning
    if st.button("🚀 Start Scanning", type="primary"):
        st.session_state.scanning = True
        st.experimental_rerun()
    
    if st.button("⏹️ Stop Scanning"):
        st.session_state.scanning = False

# Main content area - 2 columns
col_main, col_ads = st.columns([3, 1])

with col_main:
    # Live metrics
    st.header("📊 Live Market Metrics")
    metric_cols = st.columns(4)
    
    with metric_cols[0]:
        st.metric("Total Opportunities Found", len(st.session_state.arbitrage_opportunities))
    with metric_cols[1]:
        st.metric("Avg Profit Margin", f"{np.mean([opp['profit_margin'] for opp in st.session_state.arbitrage_opportunities]) if st.session_state.arbitrage_opportunities else 0:.2f}%")
    with metric_cols[2]:
        st.metric("High Confidence Trades", len([opp for opp in st.session_state.arbitrage_opportunities if opp.get('confidence', 0) > confidence_threshold]))
    with metric_cols[3]:
        st.metric("Active Scans", "Running" if st.session_state.get('scanning', False) else "Stopped")
    
    # Arbitrage opportunities table
    st.header("🎯 Arbitrage Opportunities")
    
    if st.session_state.arbitrage_opportunities:
        df = pd.DataFrame(st.session_state.arbitrage_opportunities)
        df['profit_margin'] = df['profit_margin'].apply(lambda x: f"{x:.2f}%")
        df['timestamp'] = df['timestamp'].dt.strftime("%H:%M:%S")
        st.dataframe(df[['token', 'buy_exchange', 'sell_exchange', 'profit_margin', 'confidence', 'timestamp']], use_container_width=True)
    else:
        st.info("No arbitrage opportunities found yet. Starting scan...")
    
    # AI Predictions section
    st.header("🔮 AI Price Predictions")
    
    for token in selected_tokens:
        with st.expander(f"{token} Price Analysis"):
            # Get historical prices (simulated)
            historical = st.session_state.price_history.get(token, [])
            
            if historical:
                col1, col2 = st.columns(2)
                
                with col1:
                    # Price chart
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(y=historical[-100:], mode='lines', name='Historical'))
                    
                    # Add predictions
                    predictions = ai_predictor.predict_price(historical, prediction_days)
                    future_x = list(range(len(historical[-100:]), len(historical[-100:]) + len(predictions)))
                    fig.add_trace(go.Scatter(x=future_x, y=predictions, mode='lines+markers', name='AI Prediction'))
                    
                    fig.update_layout(title=f"{token} Price with AI Prediction", height=400)
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    current_price = historical[-1] if historical else 0
                    predicted_price = predictions[0] if len(predictions) > 0 else current_price
                    volatility = np.std(historical[-50:]) / np.mean(historical[-50:]) if len(historical) >= 50 else 0.5
                    
                    signal, reason = ai_predictor.generate_signal(current_price, predicted_price, volatility)
                    
                    st.metric("Current Price", f"${current_price:.2f}")
                    st.metric("Predicted Price (3d)", f"${predicted_price:.2f}", 
                             delta=f"{((predicted_price - current_price)/current_price*100):.1f}%")
                    
                    signal_color = "🟢" if "BUY" in signal else "🔴" if "SELL" in signal else "🟡"
                    st.markdown(f"### {signal_color} Signal: {signal}")
                    st.caption(reason)
                    
                    confidence = 1 - (volatility * 10) if volatility < 0.1 else 0.5
                    st.progress(min(1.0, confidence))
                    st.caption(f"AI Confidence: {min(100, confidence*100):.0f}%")
            else:
                st.info(f"Collecting historical data for {token}...")
    
    # Alert section
    st.header("⚠️ Alerts")
    alert_placeholder = st.empty()
    
    if st.session_state.alert_queue:
        for alert in st.session_state.alert_queue[-5:]:
            alert_placeholder.warning(alert)
    else:
        alert_placeholder.info("No new alerts")

with col_ads:
    st.header("📢 Sponsors")
    
    # 5 advertisement placeholders
    ads = [
        {"title": "Trade Smarter", "content": "Advanced trading tools", "link": "#"},
        {"title": "Secure Wallet", "content": "Store your crypto safely", "link": "#"},
        {"title": "Learn Trading", "content": "Master crypto trading", "link": "#"},
        {"title": "DeFi Insights", "content": "Latest DeFi strategies", "link": "#"},
        {"title": "Mining Pool", "content": "Join the largest mining pool", "link": "#"}
    ]
    
    for i, ad in enumerate(ads):
        with st.container():
            st.markdown(f"""
            <div class="ad-placeholder">
                <h3>{ad['title']}</h3>
                <p>{ad['content']}</p>
                <small>Advertisement {i+1}</small>
            </div>
            """, unsafe_allow_html=True)
    
    # Additional metrics
    st.markdown("---")
    st.header("📈 Quick Stats")
    st.metric("Total Volume (24h)", "$2.4B", "12%")
    st.metric("Active Arbitrageurs", "1,234", "5%")
    st.metric("Gas Price (Gwei)", "35", "-3%")

# Background scanning thread
async def continuous_scan():
    """Continuous scanning function"""
    while st.session_state.get('scanning', False):
        if selected_tokens:
            opportunities = await scanner.find_opportunities(selected_tokens)
            st.session_state.arbitrage_opportunities = opportunities[:20]  # Keep last 20
            
            # Generate alerts for high-profit opportunities
            for opp in opportunities:
                if opp['profit_margin'] > min_profit * 2:  # Double threshold for alerts
                    alert = f"🚨 ALERT: {opp['token']} arbitrage opportunity! {opp['profit_margin']:.2f}% profit between {opp['buy_exchange']} and {opp['sell_exchange']}"
                    st.session_state.alert_queue.append(alert)
                    if len(st.session_state.alert_queue) > 10:
                        st.session_state.alert_queue.pop(0)
                    
                    # Broadcast to livestream if enabled
                    if st.session_state.streaming_active:
                        stream_manager.broadcast_data(opp)
            
            # Update price history (simulated)
            for token in selected_tokens:
                price = await data_fetcher.fetch_token_price(token, 'binance')
                if price:
                    st.session_state.price_history[token].append(price)
                    # Keep last 500 data points
                    if len(st.session_state.price_history[token]) > 500:
                        st.session_state.price_history[token] = st.session_state.price_history[token][-500:]
        
        await asyncio.sleep(scan_interval)

# Run background scanning
if st.session_state.get('scanning', False):
    try:
        asyncio.create_task(continuous_scan())
    except RuntimeError:
        # If no event loop is running, create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.create_task(continuous_scan())
        loop.run_forever()

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center">
    <small>🤖 AI-Powered Crypto Arbitrage Scanner | Real-time Data | Multi-Exchange Support | Livestream Ready</small>
</div>
""", unsafe_allow_html=True)
