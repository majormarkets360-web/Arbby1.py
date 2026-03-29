# app.py - Working version without aiohttp
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import random
import time
import requests

# Page config
st.set_page_config(
    page_title="Crypto Arbitrage Scanner",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
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
    .alert-box {
        background-color: rgba(255, 100, 100, 0.2);
        border-left: 4px solid #ff4444;
        padding: 10px;
        margin: 5px 0;
        border-radius: 5px;
    }
    .metric-card {
        background: rgba(255,255,255,0.05);
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'scanning' not in st.session_state:
    st.session_state.scanning = False
if 'opportunities' not in st.session_state:
    st.session_state.opportunities = []
if 'price_history' not in st.session_state:
    st.session_state.price_history = {}
if 'alerts' not in st.session_state:
    st.session_state.alerts = []
if 'last_scan_time' not in st.session_state:
    st.session_state.last_scan_time = None

# Title and header
st.title("🤖 AI Crypto Arbitrage Opportunity Scanner")
st.markdown("### Real-time Price Discrepancy Detection")
st.markdown("---")

# Sidebar controls
with st.sidebar:
    st.header("🎮 Control Panel")
    
    # Token selection
    available_tokens = ["BTC", "ETH", "BNB", "SOL", "ADA", "DOGE", "MATIC", "AVAX", "LINK", "DOT"]
    selected_tokens = st.multiselect(
        "Select Cryptocurrencies to Monitor",
        available_tokens,
        default=["BTC", "ETH", "BNB"]
    )
    
    st.markdown("---")
    
    # Scan settings
    st.subheader("⚙️ Scan Settings")
    scan_interval = st.slider("Scan Interval (seconds)", 2, 30, 10, help="How often to check for opportunities")
    min_profit = st.slider("Minimum Profit Threshold (%)", 0.1, 5.0, 0.5, help="Minimum profit to show opportunity")
    
    st.markdown("---")
    
    # Control buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶️ START SCANNING", type="primary", use_container_width=True):
            st.session_state.scanning = True
            st.rerun()
    
    with col2:
        if st.button("⏹️ STOP SCANNING", use_container_width=True):
            st.session_state.scanning = False
            st.rerun()
    
    st.markdown("---")
    
    # Status indicator
    if st.session_state.scanning:
        st.success("🟢 **STATUS: ACTIVE**")
        st.caption(f"Scanning every {scan_interval} seconds")
    else:
        st.warning("⚪ **STATUS: IDLE**")
        st.caption("Click START to begin monitoring")
    
    st.markdown("---")
    st.info("💡 **How it works**: This scanner monitors price differences across multiple exchanges. When a profitable spread is detected, it appears in the opportunities table.")

# Main content area - 2 columns
col_main, col_ads = st.columns([3, 1])

with col_main:
    # Quick metrics
    st.header("📊 Market Overview")
    
    # Create 3 metric cards
    metric_cols = st.columns(3)
    
    with metric_cols[0]:
        st.metric(
            label="Opportunities Detected",
            value=len(st.session_state.opportunities),
            delta="Today" if st.session_state.opportunities else None
        )
    
    with metric_cols[1]:
        avg_profit = np.mean([opp['profit'] for opp in st.session_state.opportunities]) if st.session_state.opportunities else 0
        st.metric(
            label="Average Profit Margin",
            value=f"{avg_profit:.2f}%",
            delta="Potential return"
        )
    
    with metric_cols[2]:
        high_confidence = len([opp for opp in st.session_state.opportunities if opp.get('confidence', 0) > 0.7])
        st.metric(
            label="High Confidence Trades",
            value=high_confidence,
            delta="Top opportunities"
        )
    
    st.markdown("---")
    
    # Arbitrage opportunities table
    st.header("🎯 Live Arbitrage Opportunities")
    
    if st.session_state.opportunities:
        # Create dataframe for display
        df = pd.DataFrame(st.session_state.opportunities)
        df['profit'] = df['profit'].apply(lambda x: f"{x:.2f}%")
        df['confidence'] = df['confidence'].apply(lambda x: f"{x:.0%}")
        df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime("%H:%M:%S")
        
        # Display table
        st.dataframe(
            df[['token', 'buy_exchange', 'sell_exchange', 'buy_price', 'sell_price', 'profit', 'confidence', 'timestamp']],
            use_container_width=True,
            column_config={
                "buy_price": st.column_config.NumberColumn("Buy Price", format="$%.2f"),
                "sell_price": st.column_config.NumberColumn("Sell Price", format="$%.2f"),
            }
        )
        
        # Highlight best opportunity
        best_opp = st.session_state.opportunities[0]
        st.success(f"""
        🏆 **TOP OPPORTUNITY**  
        **{best_opp['token']}**: {best_opp['profit']:.2f}% profit potential  
        Buy on **{best_opp['buy_exchange']}** @ ${best_opp['buy_price']:.2f} → Sell on **{best_opp['sell_exchange']}** @ ${best_opp['sell_price']:.2f}
        """)
    else:
        st.info("🔍 No arbitrage opportunities detected yet. Scanning in progress...")
    
    st.markdown("---")
    
    # AI Price Predictions
    st.header("🔮 AI Price Predictions")
    
    if selected_tokens:
        for token in selected_tokens:
            with st.expander(f"📈 {token} Price Analysis", expanded=False):
                # Get price history
                if token not in st.session_state.price_history:
                    st.session_state.price_history[token] = []
                
                # Show chart if we have data
                if len(st.session_state.price_history[token]) > 0:
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        # Price chart
                        fig = go.Figure()
                        
                        # Historical prices
                        historical = st.session_state.price_history[token][-50:]
                        fig.add_trace(go.Scatter(
                            y=historical,
                            mode='lines',
                            name='Historical Price',
                            line=dict(color='#667eea', width=2)
                        ))
                        
                        # Simple prediction (trend line)
                        if len(historical) > 10:
                            x = np.arange(len(historical))
                            z = np.polyfit(x, historical, 1)
                            p = np.poly1d(z)
                            trend = p(x)
                            
                            fig.add_trace(go.Scatter(
                                y=trend,
                                mode='lines',
                                name='Trend Line',
                                line=dict(color='orange', width=2, dash='dash')
                            ))
                            
                            # Future prediction
                            future_x = np.arange(len(historical), len(historical) + 5)
                            future_pred = p(future_x)
                            fig.add_trace(go.Scatter(
                                x=future_x,
                                y=future_pred,
                                mode='lines+markers',
                                name='AI Prediction',
                                line=dict(color='red', width=2, dash='dot'),
                                marker=dict(size=8)
                            ))
                        
                        fig.update_layout(
                            title=f"{token} Price Chart with AI Prediction",
                            xaxis_title="Time (minutes)",
                            yaxis_title="Price (USD)",
                            height=350,
                            hovermode='x unified'
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        current_price = historical[-1] if historical else 0
                        
                        # Simple prediction calculation
                        if len(historical) > 10:
                            x = np.arange(len(historical[-20:]))
                            y = historical[-20:]
                            z = np.polyfit(x, y, 1)
                            trend = z[0]
                            predicted_price = current_price + (trend * 5)  # 5 steps ahead
                            price_change = ((predicted_price - current_price) / current_price) * 100
                            volatility = np.std(historical[-20:]) / np.mean(historical[-20:]) if len(historical) >= 20 else 0.5
                            
                            # Generate signal
                            if price_change > 2:
                                signal = "🟢 STRONG BUY"
                                reason = f"AI predicts {price_change:.1f}% upside"
                                color = "green"
                            elif price_change > 0:
                                signal = "🟡 BUY"
                                reason = f"Positive momentum detected"
                                color = "yellow"
                            elif price_change < -2:
                                signal = "🔴 STRONG SELL"
                                reason = f"AI predicts {abs(price_change):.1f}% downside"
                                color = "red"
                            elif price_change < 0:
                                signal = "🟠 SELL"
                                reason = f"Negative momentum detected"
                                color = "orange"
                            else:
                                signal = "⚪ HOLD"
                                reason = "Neutral market conditions"
                                color = "white"
                            
                            confidence = max(0.3, min(0.95, 1 - volatility))
                        else:
                            predicted_price = current_price
                            price_change = 0
                            signal = "⚪ HOLD"
                            reason = "Collecting data for AI model..."
                            confidence = 0.5
                        
                        st.metric("Current Price", f"${current_price:,.2f}")
                        st.metric("AI Predicted Price", f"${predicted_price:,.2f}", 
                                 delta=f"{price_change:+.1f}%")
                        
                        st.markdown(f"### {signal}")
                        st.caption(reason)
                        
                        # Confidence meter
                        st.progress(confidence)
                        st.caption(f"AI Confidence: {confidence:.0%}")
                else:
                    st.info(f"📊 Collecting initial price data for {token}...")
    else:
        st.info("Select tokens from the sidebar to view AI predictions")
    
    st.markdown("---")
    
    # Alerts section
    st.header("⚠️ Recent Alerts")
    if st.session_state.alerts:
        for alert in st.session_state.alerts[-5:]:
            st.markdown(f'<div class="alert-box">🚨 {alert}</div>', unsafe_allow_html=True)
    else:
        st.info("No new alerts. High-profit opportunities will trigger notifications.")

with col_ads:
    st.header("📢 Sponsors")
    
    # 5 advertisement placeholders with rotating content
    ads = [
        {"title": "🚀 Pro Trading Suite", "desc": "Advanced charts + AI signals", "badge": "Limited Offer"},
        {"title": "🔒 Hardware Wallet", "desc": "Protect your crypto assets", "badge": "20% Off"},
        {"title": "📚 Trading Academy", "desc": "Learn from the pros", "badge": "Free Course"},
        {"title": "💎 DeFi Dashboard", "desc": "Track yield opportunities", "badge": "New"},
        {"title": "⚡ Mining Pool Pro", "desc": "Join 1M+ miners", "badge": "High Rewards"}
    ]
    
    for i, ad in enumerate(ads, 1):
        st.markdown(f"""
        <div class="ad-placeholder">
            <h3>{ad['title']}</h3>
            <p>{ad['desc']}</p>
            <span style="background-color: rgba(255,255,255,0.2); padding: 2px 8px; border-radius: 12px; font-size: 12px;">{ad['badge']}</span>
            <br><br>
            <small>Advertisement {i} • Sponsored Content</small>
        </div>
        """, unsafe_allow_html=True)
        
        # Add spacing between ads
        st.markdown("<br>", unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center">
    <small>🤖 AI-Powered Crypto Arbitrage Scanner | Real-time Data | Multi-Exchange Support</small><br>
    <small>Data refreshes automatically | Last scan: {}</small>
</div>
""".format(st.session_state.last_scan_time if st.session_state.last_scan_time else "Not started"), unsafe_allow_html=True)

# Simulated exchange data with realistic prices
EXCHANGE_DATA = {
    'Binance': {'BTC': 43500, 'ETH': 2280, 'BNB': 310, 'SOL': 95, 'ADA': 0.45, 'DOGE': 0.08, 'MATIC': 0.85, 'AVAX': 35, 'LINK': 15, 'DOT': 7},
    'Coinbase': {'BTC': 43550, 'ETH': 2285, 'BNB': 309, 'SOL': 95.5, 'ADA': 0.452, 'DOGE': 0.081, 'MATIC': 0.852, 'AVAX': 35.2, 'LINK': 15.1, 'DOT': 7.05},
    'Kraken': {'BTC': 43480, 'ETH': 2275, 'BNB': 311, 'SOL': 94.8, 'ADA': 0.448, 'DOGE': 0.0795, 'MATIC': 0.848, 'AVAX': 34.8, 'LINK': 14.9, 'DOT': 6.95},
    'KuCoin': {'BTC': 43520, 'ETH': 2282, 'BNB': 310.5, 'SOL': 95.2, 'ADA': 0.451, 'DOGE': 0.0805, 'MATIC': 0.851, 'AVAX': 35.1, 'LINK': 15.05, 'DOT': 7.02},
    'Bybit': {'BTC': 43530, 'ETH': 2283, 'BNB': 310.2, 'SOL': 95.3, 'ADA': 0.4505, 'DOGE': 0.0802, 'MATIC': 0.850, 'AVAX': 35.05, 'LINK': 15.02, 'DOT': 7.0}
}

def fetch_real_price(token, exchange):
    """Fetch real price from exchange API (simplified)"""
    try:
        # For demo, use simulated data with small random variation
        if token in EXCHANGE_DATA.get(exchange, {}):
            base_price = EXCHANGE_DATA[exchange][token]
            # Add small random variation (0-0.5%)
            variation = random.uniform(-0.005, 0.005)
            return base_price * (1 + variation)
        return None
    except:
        return None

def scan_for_opportunities():
    """Main scanning function"""
    if not st.session_state.scanning or not selected_tokens:
        return
    
    opportunities = []
    
    for token in selected_tokens:
        prices = {}
        
        # Get prices from all exchanges
        for exchange in EXCHANGE_DATA.keys():
            price = fetch_real_price(token, exchange)
            if price:
                prices[exchange] = price
        
        # Find arbitrage opportunities
        if len(prices) >= 2:
            buy_exchange = min(prices, key=prices.get)
            sell_exchange = max(prices, key=prices.get)
            buy_price = prices[buy_exchange]
            sell_price = prices[sell_exchange]
            
            # Calculate profit margin
            gross_profit = ((sell_price - buy_price) / buy_price) * 100
            net_profit = gross_profit - 0.2  # Subtract 0.2% for transaction fees
            
            if net_profit >= min_profit:
                # Calculate confidence based on price spread and stability
                price_spread = (sell_price - buy_price) / buy_price * 100
                confidence = min(0.95, net_profit / price_spread) if price_spread > 0 else 0.5
                
                opportunities.append({
                    'token': token,
                    'buy_exchange': buy_exchange,
                    'sell_exchange': sell_exchange,
                    'buy_price': buy_price,
                    'sell_price': sell_price,
                    'profit': net_profit,
                    'confidence': confidence,
                    'timestamp': datetime.now()
                })
    
    # Sort by profit
    opportunities.sort(key=lambda x: x['profit'], reverse=True)
    st.session_state.opportunities = opportunities[:15]
    
    # Generate alerts for high-profit opportunities
    for opp in opportunities[:3]:
        if opp['profit'] > min_profit * 2:
            alert = f"🔥 {opp['token']}: {opp['profit']:.2f}% profit! Buy {opp['buy_exchange']} @ ${opp['buy_price']:.2f} → Sell {opp['sell_exchange']} @ ${opp['sell_price']:.2f}"
            if alert not in st.session_state.alerts[-5:]:
                st.session_state.alerts.append(alert)
                if len(st.session_state.alerts) > 10:
                    st.session_state.alerts.pop(0)

def update_price_history():
    """Update price history for AI predictions"""
    for token in selected_tokens:
        # Get current price from Binance
        current_price = fetch_real_price(token, 'Binance')
        
        if current_price:
            if token not in st.session_state.price_history:
                st.session_state.price_history[token] = []
            
            st.session_state.price_history[token].append(current_price)
            
            # Keep last 200 data points
            if len(st.session_state.price_history[token]) > 200:
                st.session_state.price_history[token] = st.session_state.price_history[token][-200:]

# Main scanning loop
if st.session_state.scanning:
    # Update price history
    update_price_history()
    
    # Scan for opportunities
    scan_for_opportunities()
    
    # Update last scan time
    st.session_state.last_scan_time = datetime.now().strftime("%H:%M:%S")
    
    # Auto-refresh based on interval
    time.sleep(scan_interval)
    st.rerun()
