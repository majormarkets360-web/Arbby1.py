# app.py - Enhanced version with more tokens and exchanges
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import random
import time
import requests
import json

# Page config
st.set_page_config(
    page_title="Ultimate Crypto Arbitrage Scanner",
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
        transition: transform 0.3s;
    }
    .ad-placeholder:hover {
        transform: translateY(-5px);
        transition: transform 0.3s;
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
        animation: slideIn 0.5s;
    }
    @keyframes slideIn {
        from {
            transform: translateX(-100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    .exchange-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: bold;
        margin: 2px;
    }
    .cex-badge {
        background-color: #3498db;
        color: white;
    }
    .dex-badge {
        background-color: #9b59b6;
        color: white;
    }
    .profit-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        color: white;
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
if 'selected_exchanges' not in st.session_state:
    st.session_state.selected_exchanges = []
if 'selected_tokens' not in st.session_state:
    st.session_state.selected_tokens = []

# Comprehensive list of cryptocurrencies by category
CRYPTO_CATEGORIES = {
    "🏆 Top 10": ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "DOGE", "AVAX", "MATIC", "LINK"],
    "🚀 Layer 1": ["SOL", "AVAX", "NEAR", "FTM", "ATOM", "ALGO", "VET", "HBAR", "ICP", "APT"],
    "💎 DeFi": ["UNI", "AAVE", "MKR", "COMP", "SNX", "CRV", "CAKE", "SUSHI", "LDO", "1INCH"],
    "🔗 Layer 2": ["MATIC", "ARB", "OP", "BOBA", "METIS", "IMX", "SKL", "LRC", "ZKSYNC", "MNT"],
    "🎮 Gaming & Metaverse": ["SAND", "MANA", "AXS", "GALA", "ENJ", "ILV", "YGG", "ALICE", "SLP", "WEMIX"],
    "💲 Stablecoins": ["USDT", "USDC", "DAI", "BUSD", "USTC", "FRAX", "LUSD", "MIM", "TUSD", "USDD"],
    "🌉 Cross-chain": ["DOT", "ATOM", "RUNE", "ZIL", "WAN", "KAVA", "AXL", "CRO", "REN", "SYN"],
    "🔒 Privacy": ["XMR", "ZEC", "DASH", "SCRT", "KEEP", "NU", "NYM", "ROSE", "PIRATE", "FIRO"],
    "🏦 Exchange Tokens": ["BNB", "OKB", "CRO", "KCS", "HT", "GT", "LEO", "BGB", "MX", "FTT"],
    "🌱 Meme Coins": ["DOGE", "SHIB", "PEPE", "FLOKI", "BONK", "WIF", "MEME", "SAMO", "COQ", "BABYDOGE"],
    "📊 Oracles": ["LINK", "PYTH", "BAND", "API3", "TRB", "NEST", "UMB", "RAI", "DIA", "RLC"],
    "🔮 AI Coins": ["FET", "AGIX", "OCEAN", "RNDR", "TAO", "GRT", "ALI", "NUM", "ORAI", "CTXC"]
}

# Comprehensive exchange list with types
EXCHANGES = {
    # Centralized Exchanges (CEX)
    "CEX - Binance": {"type": "CEX", "url": "https://api.binance.com", "fee": 0.001},
    "CEX - Coinbase": {"type": "CEX", "url": "https://api.coinbase.com", "fee": 0.005},
    "CEX - Kraken": {"type": "CEX", "url": "https://api.kraken.com", "fee": 0.0026},
    "CEX - KuCoin": {"type": "CEX", "url": "https://api.kucoin.com", "fee": 0.001},
    "CEX - Bybit": {"type": "CEX", "url": "https://api.bybit.com", "fee": 0.001},
    "CEX - OKX": {"type": "CEX", "url": "https://www.okx.com", "fee": 0.001},
    "CEX - Huobi": {"type": "CEX", "url": "https://api.huobi.pro", "fee": 0.002},
    "CEX - Gate.io": {"type": "CEX", "url": "https://api.gateio.ws", "fee": 0.002},
    "CEX - Bitget": {"type": "CEX", "url": "https://api.bitget.com", "fee": 0.001},
    "CEX - MEXC": {"type": "CEX", "url": "https://api.mexc.com", "fee": 0.002},
    
    # Decentralized Exchanges (DEX) - Ethereum
    "DEX - Uniswap V2": {"type": "DEX", "chain": "Ethereum", "fee": 0.003, "protocol": "uniswap"},
    "DEX - Uniswap V3": {"type": "DEX", "chain": "Ethereum", "fee": 0.003, "protocol": "uniswap_v3"},
    "DEX - SushiSwap": {"type": "DEX", "chain": "Ethereum", "fee": 0.003, "protocol": "sushiswap"},
    "DEX - Curve": {"type": "DEX", "chain": "Ethereum", "fee": 0.0004, "protocol": "curve"},
    "DEX - Balancer": {"type": "DEX", "chain": "Ethereum", "fee": 0.003, "protocol": "balancer"},
    
    # DEX - BSC
    "DEX - PancakeSwap V2": {"type": "DEX", "chain": "BSC", "fee": 0.0025, "protocol": "pancakeswap"},
    "DEX - PancakeSwap V3": {"type": "DEX", "chain": "BSC", "fee": 0.0025, "protocol": "pancakeswap_v3"},
    "DEX - Biswap": {"type": "DEX", "chain": "BSC", "fee": 0.001, "protocol": "biswap"},
    "DEX - ApeSwap": {"type": "DEX", "chain": "BSC", "fee": 0.002, "protocol": "apeswap"},
    "DEX - BabySwap": {"type": "DEX", "chain": "BSC", "fee": 0.002, "protocol": "babyswap"},
    
    # DEX - Polygon
    "DEX - QuickSwap": {"type": "DEX", "chain": "Polygon", "fee": 0.003, "protocol": "quickswap"},
    "DEX - SushiSwap (Polygon)": {"type": "DEX", "chain": "Polygon", "fee": 0.003, "protocol": "sushiswap"},
    "DEX - Balancer (Polygon)": {"type": "DEX", "chain": "Polygon", "fee": 0.003, "protocol": "balancer"},
    "DEX - Curve (Polygon)": {"type": "DEX", "chain": "Polygon", "fee": 0.0004, "protocol": "curve"},
    
    # DEX - Solana
    "DEX - Raydium": {"type": "DEX", "chain": "Solana", "fee": 0.0025, "protocol": "raydium"},
    "DEX - Orca": {"type": "DEX", "chain": "Solana", "fee": 0.003, "protocol": "orca"},
    "DEX - Saber": {"type": "DEX", "chain": "Solana", "fee": 0.0001, "protocol": "saber"},
    
    # DEX - Arbitrum
    "DEX - Camelot": {"type": "DEX", "chain": "Arbitrum", "fee": 0.003, "protocol": "camelot"},
    "DEX - GMX": {"type": "DEX", "chain": "Arbitrum", "fee": 0.003, "protocol": "gmx"},
    
    # DEX - Avalanche
    "DEX - Trader Joe": {"type": "DEX", "chain": "Avalanche", "fee": 0.003, "protocol": "traderjoe"},
    "DEX - Pangolin": {"type": "DEX", "chain": "Avalanche", "fee": 0.003, "protocol": "pangolin"},
    
    # DEX - Optimism
    "DEX - Velodrome": {"type": "DEX", "chain": "Optimism", "fee": 0.003, "protocol": "velodrome"},
    
    # DEX - Base
    "DEX - Aerodrome": {"type": "DEX", "chain": "Base", "fee": 0.003, "protocol": "aerodrome"}
}

# Generate complete token list from all categories
ALL_TOKENS = []
for category, tokens in CRYPTO_CATEGORIES.items():
    ALL_TOKENS.extend(tokens)
ALL_TOKENS = sorted(list(set(ALL_TOKENS)))  # Remove duplicates and sort

# Title and header
st.title("🤖 Ultimate AI Crypto Arbitrage Scanner")
st.markdown("### Multi-Exchange & Cross-Chain Opportunity Detector")
st.markdown("---")

# Sidebar controls
with st.sidebar:
    st.header("🎮 Control Panel")
    
    # Exchange selection
    st.subheader("🏦 Exchange Selection")
    st.caption("Select exchanges to monitor (more exchanges = better opportunities)")
    
    # Filter exchanges by type
    exchange_filter = st.multiselect(
    "Filter by type",
    ["All", "CEX", "DEX - Ethereum", "DEX - BSC", "DEX - Polygon", "DEX - Solana", "DEX - Arbitrum", "DEX - Avalanche", "DEX - Optimism", "DEX - Base"],
    default=["All"]
)
    
    # Display exchanges based on filter
    available_exchanges = []
    if "All" in exchange_filter:
        available_exchanges = list(EXCHANGES.keys())
    else:
        for exchange_name in EXCHANGES.keys():
            for filter_item in exchange_filter:
                if filter_item in exchange_name:
                    available_exchanges.append(exchange_name)
                    break
    
    selected_exchanges = st.multiselect(
        "Select exchanges to scan",
        available_exchanges,
        default=[ex for ex in available_exchanges[:15]]  # Default to first 15 exchanges
    )
    
    st.markdown("---")
    
    # Token selection with categories
    st.subheader("🪙 Token Selection")
    
    # Category selection for tokens
    selected_categories = st.multiselect(
        "Filter tokens by category",
        list(CRYPTO_CATEGORIES.keys()),
        default=["🏆 Top 10", "🚀 Layer 1", "💎 DeFi"]
    )
    
    # Show tokens from selected categories
    category_tokens = []
    for cat in selected_categories:
        category_tokens.extend(CRYPTO_CATEGORIES.get(cat, []))
    category_tokens = list(set(category_tokens))
    
    # Search/filter tokens
    token_search = st.text_input("🔍 Search tokens", placeholder="e.g., BTC, ETH, UNI...")
    
    if token_search:
        filtered_tokens = [t for t in category_tokens if token_search.upper() in t]
    else:
        filtered_tokens = category_tokens
    
    selected_tokens = st.multiselect(
        f"Select tokens to monitor ({len(filtered_tokens)} available)",
        filtered_tokens,
        default=[t for t in filtered_tokens[:10]]  # Default to first 10 tokens
    )
    
    st.markdown("---")
    
    # Scan settings
    st.subheader("⚙️ Scan Settings")
    col1, col2 = st.columns(2)
    with col1:
        scan_interval = st.slider("Scan Interval (seconds)", 2, 30, 10)
    with col2:
        min_profit = st.slider("Min Profit Threshold (%)", 0.1, 10.0, 0.5)
    
    # Advanced settings
    with st.expander("⚡ Advanced Settings"):
        gas_fee_buffer = st.slider("Gas Fee Buffer (%)", 0.1, 2.0, 0.5, 
                                   help="Extra buffer for DEX gas fees")
        volatility_filter = st.slider("Min Volatility Filter (%)", 0, 10, 2,
                                      help="Ignore opportunities below this volatility")
        max_slippage = st.slider("Max Slippage (%)", 0.1, 2.0, 0.5,
                                help="Maximum acceptable price slippage")
    
    st.markdown("---")
    
    # Control buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶️ START SCANNING", type="primary", use_container_width=True):
            st.session_state.scanning = True
            st.session_state.selected_exchanges = selected_exchanges
            st.session_state.selected_tokens = selected_tokens
            st.rerun()
    
    with col2:
        if st.button("⏹️ STOP SCANNING", use_container_width=True):
            st.session_state.scanning = False
            st.rerun()
    
    st.markdown("---")
    
    # Status indicator
    if st.session_state.scanning:
        st.success("🟢 **STATUS: ACTIVE**")
        st.caption(f"Monitoring {len(selected_exchanges)} exchanges")
        st.caption(f"Tracking {len(selected_tokens)} tokens")
        st.caption(f"Scanning every {scan_interval}s")
    else:
        st.warning("⚪ **STATUS: IDLE**")
        st.caption("Click START to begin monitoring")
    
    st.markdown("---")
    
    # Stats
    st.subheader("📊 Session Stats")
    if st.session_state.opportunities:
        total_profit = sum([opp['profit'] for opp in st.session_state.opportunities])
        avg_confidence = np.mean([opp['confidence'] for opp in st.session_state.opportunities])
        st.metric("Total Opportunities", len(st.session_state.opportunities))
        st.metric("Total Potential Profit", f"{total_profit:.2f}%")
        st.metric("Avg Confidence", f"{avg_confidence:.1%}")
    
    st.markdown("---")
    st.info("💡 **Pro Tip**: Enable more exchanges and tokens to find hidden arbitrage opportunities across chains!")

# Main content area - 2 columns
col_main, col_ads = st.columns([3, 1])

with col_main:
    # Quick metrics
    st.header("📊 Live Market Overview")
    
    metric_cols = st.columns(4)
    
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
    
    with metric_cols[3]:
        active_exchanges = len(set([opp['buy_exchange'] for opp in st.session_state.opportunities] + 
                                   [opp['sell_exchange'] for opp in st.session_state.opportunities]))
        st.metric(
            label="Active Exchanges",
            value=active_exchanges if st.session_state.opportunities else 0,
            delta="With opportunities"
        )
    
    st.markdown("---")
    
    # Arbitrage opportunities table
    st.header("🎯 Live Arbitrage Opportunities")
    
    # Add filters for opportunities
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    with col_filter1:
        min_profit_filter = st.slider("Min Profit %", 0.0, 10.0, 0.0, key="profit_filter")
    with col_filter2:
        min_confidence_filter = st.slider("Min Confidence", 0.0, 1.0, 0.0, key="confidence_filter")
    with col_filter3:
        opp_type = st.selectbox("Opportunity Type", ["All", "CEX-CEX", "DEX-DEX", "CEX-DEX"])
    
    if st.session_state.opportunities:
        # Filter opportunities
        filtered_opps = [opp for opp in st.session_state.opportunities 
                        if opp['profit'] >= min_profit_filter 
                        and opp['confidence'] >= min_confidence_filter]
        
        if opp_type != "All":
            if opp_type == "CEX-CEX":
                filtered_opps = [opp for opp in filtered_opps if "CEX" in opp['buy_exchange'] and "CEX" in opp['sell_exchange']]
            elif opp_type == "DEX-DEX":
                filtered_opps = [opp for opp in filtered_opps if "DEX" in opp['buy_exchange'] and "DEX" in opp['sell_exchange']]
            elif opp_type == "CEX-DEX":
                filtered_opps = [opp for opp in filtered_opps if ("CEX" in opp['buy_exchange'] and "DEX" in opp['sell_exchange']) or
                                                                  ("DEX" in opp['buy_exchange'] and "CEX" in opp['sell_exchange'])]
        
        if filtered_opps:
            # Create dataframe for display
            df = pd.DataFrame(filtered_opps)
            df['profit'] = df['profit'].apply(lambda x: f"{x:.2f}%")
            df['confidence'] = df['confidence'].apply(lambda x: f"{x:.0%}")
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime("%H:%M:%S")
            
            # Add exchange type badges
            df['buy_type'] = df['buy_exchange'].apply(lambda x: "CEX" if "CEX" in x else "DEX")
            df['sell_type'] = df['sell_exchange'].apply(lambda x: "CEX" if "CEX" in x else "DEX")
            
            # Display table
            st.dataframe(
                df[['token', 'buy_exchange', 'sell_exchange', 'buy_price', 'sell_price', 'profit', 'confidence', 'timestamp']],
                use_container_width=True,
                column_config={
                    "buy_price": st.column_config.NumberColumn("Buy Price", format="$%.4f"),
                    "sell_price": st.column_config.NumberColumn("Sell Price", format="$%.4f"),
                    "profit": st.column_config.TextColumn("Profit", help="After fees"),
                }
            )
            
            # Highlight best opportunity
            best_opp = filtered_opps[0]
            st.success(f"""
            🏆 **TOP OPPORTUNITY - {best_opp['profit']:.2f}% PROFIT POTENTIAL**
            
            **Token**: {best_opp['token']}
            **Buy**: {best_opp['buy_exchange']} @ ${best_opp['buy_price']:.4f}
            **Sell**: {best_opp['sell_exchange']} @ ${best_opp['sell_price']:.4f}
            **Confidence**: {best_opp['confidence']:.0%}
            **Est. Profit per $1000**: ${best_opp['profit'] * 10:.2f}
            """)
        else:
            st.info(f"No opportunities match your filters. Try lowering the thresholds.")
    else:
        st.info("🔍 No arbitrage opportunities detected yet. Scanning in progress...")
    
    st.markdown("---")
    
    # Cross-chain arbitrage section
    st.header("🌉 Cross-Chain Arbitrage Opportunities")
    st.caption("Price differences between the same token on different blockchains")
    
    cross_chain_opps = [opp for opp in st.session_state.opportunities 
                       if "DEX" in opp['buy_exchange'] and "DEX" in opp['sell_exchange'] 
                       and EXCHANGES.get(opp['buy_exchange'], {}).get('chain') != EXCHANGES.get(opp['sell_exchange'], {}).get('chain')]
    
    if cross_chain_opps:
        for opp in cross_chain_opps[:3]:
            buy_chain = EXCHANGES.get(opp['buy_exchange'], {}).get('chain', 'Unknown')
            sell_chain = EXCHANGES.get(opp['sell_exchange'], {}).get('chain', 'Unknown')
            st.info(f"""
            **{opp['token']}**: {buy_chain} → {sell_chain}
            Profit: **{opp['profit']:.2f}%** | Confidence: {opp['confidence']:.0%}
            Bridge cost not included - verify gas fees
            """)
    else:
        st.info("No cross-chain opportunities detected yet.")
    
    st.markdown("---")
    
    # AI Price Predictions
    st.header("🔮 AI Price Predictions & Signals")
    
    if selected_tokens:
        # Create tabs for different prediction views
        pred_tabs = st.tabs(["📈 Price Charts", "🎯 Trading Signals", "📊 Market Sentiment"])
        
        with pred_tabs[0]:
            for token in selected_tokens[:3]:  # Show top 3 tokens
                with st.expander(f"📈 {token} Price Analysis", expanded=False):
                    # Get price history
                    if token not in st.session_state.price_history:
                        st.session_state.price_history[token] = []
                    
                    # Show chart if we have data
                    if len(st.session_state.price_history[token]) > 0:
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            # Price chart with technical indicators
                            historical = st.session_state.price_history[token][-100:]
                            
                            fig = go.Figure()
                            
                            # Candlestick-like price chart
                            fig.add_trace(go.Scatter(
                                y=historical,
                                mode='lines',
                                name='Price',
                                line=dict(color='#667eea', width=2),
                                fill='tozeroy',
                                fillcolor='rgba(102, 126, 234, 0.2)'
                            ))
                            
                            # Moving averages
                            if len(historical) > 20:
                                ma7 = pd.Series(historical).rolling(7).mean()
                                ma25 = pd.Series(historical).rolling(25).mean()
                                
                                fig.add_trace(go.Scatter(
                                    y=ma7,
                                    mode='lines',
                                    name='MA 7',
                                    line=dict(color='orange', width=1, dash='dash')
                                ))
                                
                                fig.add_trace(go.Scatter(
                                    y=ma25,
                                    mode='lines',
                                    name='MA 25',
                                    line=dict(color='red', width=1, dash='dot')
                                ))
                            
                            # Simple prediction (trend line)
                            if len(historical) > 10:
                                x = np.arange(len(historical))
                                z = np.polyfit(x, historical, 1)
                                p = np.poly1d(z)
                                trend = p(x)
                                
                                # Future prediction
                                future_x = np.arange(len(historical), len(historical) + 10)
                                future_pred = p(future_x)
                                fig.add_trace(go.Scatter(
                                    x=future_x,
                                    y=future_pred,
                                    mode='lines+markers',
                                    name='AI Prediction (10 steps)',
                                    line=dict(color='red', width=2, dash='dot'),
                                    marker=dict(size=6)
                                ))
                            
                            fig.update_layout(
                                title=f"{token} Price Chart with Technical Indicators",
                                xaxis_title="Time (minutes)",
                                yaxis_title="Price (USD)",
                                height=400,
                                hovermode='x unified'
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        
                        with col2:
                            current_price = historical[-1] if historical else 0
                            
                            # Calculate technical indicators
                            if len(historical) > 20:
                                rsi = calculate_rsi(historical)
                                macd, signal = calculate_macd(historical)
                                volatility = np.std(historical[-20:]) / np.mean(historical[-20:])
                                
                                # Generate comprehensive signal
                                signal, strength, reason = generate_advanced_signal(
                                    historical, current_price, volatility
                                )
                                
                                st.metric("Current Price", f"${current_price:,.4f}")
                                st.metric("24h Change", f"{((historical[-1] - historical[-24])/historical[-24]*100):+.2f}%" if len(historical) > 24 else "N/A")
                                st.metric("RSI", f"{rsi:.1f}", help="Relative Strength Index")
                                st.metric("Volatility", f"{volatility:.2%}")
                                
                                st.markdown(f"""
                                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                            border-radius: 10px; padding: 15px; margin-top: 10px;">
                                    <h3 style="margin: 0;">{signal}</h3>
                                    <p style="margin: 5px 0 0 0; font-size: 12px;">{reason}</p>
                                    <div style="margin-top: 10px;">
                                        <div style="background: rgba(255,255,255,0.2); border-radius: 10px; height: 6px;">
                                            <div style="background: {'#00ff00' if strength > 0 else '#ff4444'}; 
                                                        width: {abs(strength)}%; height: 6px; border-radius: 10px;"></div>
                                        </div>
                                        <p style="margin: 5px 0 0 0; font-size: 11px;">Signal Strength: {abs(strength):.0%}</p>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                confidence = max(0.3, min(0.95, 1 - volatility))
                                st.progress(confidence)
                                st.caption(f"AI Model Confidence: {confidence:.0%}")
                            else:
                                st.info(f"Collecting data for {token}... Need {20 - len(historical)} more data points")
                    else:
                        st.info(f"📊 Collecting initial price data for {token}...")
        
        with pred_tabs[1]:
            st.subheader("🎯 Real-time Trading Signals")
            
            # Create signal table
            signals_data = []
            for token in selected_tokens[:10]:
                if token in st.session_state.price_history and len(st.session_state.price_history[token]) > 20:
                    historical = st.session_state.price_history[token][-50:]
                    current = historical[-1]
                    volatility = np.std(historical[-20:]) / np.mean(historical[-20:])
                    signal, strength, reason = generate_advanced_signal(historical, current, volatility)
                    
                    signals_data.append({
                        "Token": token,
                        "Signal": signal,
                        "Strength": f"{strength:.0%}",
                        "Confidence": f"{max(0.3, min(0.95, 1 - volatility)):.0%}",
                        "Reason": reason[:50] + "..."
                    })
            
            if signals_data:
                st.dataframe(pd.DataFrame(signals_data), use_container_width=True)
            else:
                st.info("Gathering data for signal generation...")
        
        with pred_tabs[2]:
            st.subheader("📊 Market Sentiment Analysis")
            
            # Create sentiment gauge for each token
            for token in selected_tokens[:5]:
                if token in st.session_state.price_history and len(st.session_state.price_history[token]) > 20:
                    historical = st.session_state.price_history[token][-50:]
                    
                    # Calculate sentiment metrics
                    price_trend = (historical[-1] - historical[-10]) / historical[-10] if len(historical) > 10 else 0
                    volatility = np.std(historical[-20:]) / np.mean(historical[-20:])
                    momentum = historical[-1] - historical[-5] if len(historical) > 5 else 0
                    
                    # Calculate sentiment score (-1 to 1)
                    sentiment_score = np.clip(price_trend * 10 + momentum / historical[-1], -1, 1)
                    
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        st.markdown(f"**{token}**")
                    with col2:
                        sentiment_color = "🟢" if sentiment_score > 0.2 else "🔴" if sentiment_score < -0.2 else "🟡"
                        st.markdown(f"{sentiment_color} Sentiment: {sentiment_score:+.2f}")
                    with col3:
                        st.markdown(f"Volatility: {volatility:.1%}")
                    
                    # Sentiment gauge
                    st.progress((sentiment_score + 1) / 2)
                    st.caption(f"Trend: {price_trend:+.2%} | Momentum: ${momentum:+.2f}")
                    st.markdown("---")
    else:
        st.info("Select tokens from the sidebar to view AI predictions")
    
    st.markdown("---")
    
    # Alerts section
    st.header("⚠️ Live Alerts")
    alert_container = st.container()
    
    with alert_container:
        if st.session_state.alerts:
            for alert in st.session_state.alerts[-10:]:
                st.markdown(f'<div class="alert-box">🚨 {alert}</div>', unsafe_allow_html=True)
        else:
            st.info("No new alerts. High-profit opportunities will trigger notifications.")

with col_ads:
    st.header("📢 Premium Partners")
    
    # 5 advertisement placeholders with premium content
    ads = [
        {"title": "🚀 VIP Trading Suite", "desc": "Get early access to arbitrage opportunities", "badge": "Limited Spots", "color": "#f39c12"},
        {"title": "🔒 Quantum Wallet", "desc": "Military-grade cold storage", "badge": "50% Off", "color": "#e74c3c"},
        {"title": "📚 Arbitrage Masterclass", "desc": "Learn from top traders", "badge": "Free Webinar", "color": "#3498db"},
        {"title": "💎 DeFi Yield Optimizer", "desc": "Maximize cross-chain returns", "badge": "14-Day Trial", "color": "#9b59b6"},
        {"title": "⚡ Flash Loan Pro", "desc": "Execute arbitrage with leverage", "badge": "New Feature", "color": "#1abc9c"}
    ]
    
    for i, ad in enumerate(ads, 1):
        st.markdown(f"""
        <div class="ad-placeholder" style="background: linear-gradient(135deg, {ad['color']} 0%, #2c3e50 100%);">
            <h3>{ad['title']}</h3>
            <p>{ad['desc']}</p>
            <span style="background-color: rgba(255,255,255,0.2); padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold;">{ad['badge']}</span>
            <br><br>
            <small>Advertisement {i} • Sponsored</small>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
    
    # Premium features teaser
    st.markdown("---")
    st.markdown("""
    <div style="background: rgba(102, 126, 234, 0.1); border-radius: 10px; padding: 15px;">
        <h4>💎 Premium Features</h4>
        <small>✓ Real-time WebSocket feeds</small><br>
        <small>✓ Advanced AI models</small><br>
        <small>✓ Automated execution</small><br>
        <small>✓ Priority alerts</small><br>
        <br>
        <button style="background: #667eea; color: white; border: none; padding: 8px 16px; border-radius: 5px; width: 100%;">Upgrade Now →</button>
    </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center">
    <small>🤖 Ultimate AI Crypto Arbitrage Scanner | Multi-Exchange | Cross-Chain | Real-time</small><br>
    <small>Monitoring {} exchanges • Tracking {} tokens • Last scan: {}</small>
</div>
""".format(len(selected_exchanges), len(selected_tokens), 
           st.session_state.last_scan_time if st.session_state.last_scan_time else "Not started"), 
     unsafe_allow_html=True)

# Technical indicator functions
def calculate_rsi(prices, period=14):
    """Calculate RSI technical indicator"""
    if len(prices) < period + 1:
        return 50
    
    deltas = np.diff(prices[-period-1:])
    gains = deltas[deltas > 0].sum() / period
    losses = -deltas[deltas < 0].sum() / period
    
    if losses == 0:
        return 100
    
    rs = gains / losses
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(prices, fast=12, slow=26, signal=9):
    """Calculate MACD indicator"""
    if len(prices) < slow + signal:
        return 0, 0
    
    ema_fast = pd.Series(prices).ewm(span=fast, adjust=False).mean()
    ema_slow = pd.Series(prices).ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    macd_signal = macd.ewm(span=signal, adjust=False).mean()
    
    return macd.iloc[-1], macd_signal.iloc[-1]

def generate_advanced_signal(historical, current_price, volatility):
    """Generate advanced trading signal with multiple indicators"""
    if len(historical) < 30:
        return "HOLD", 0, "Insufficient data"
    
    # Calculate indicators
    ma_7 = np.mean(historical[-7:])
    ma_25 = np.mean(historical[-25:])
    rsi = calculate_rsi(historical)
    macd, signal = calculate_macd(historical)
    
    # Trend analysis
    trend = ma_7 - ma_25
    trend_strength = min(1.0, abs(trend) / current_price * 100)
    
    # Momentum
    momentum = (historical[-1] - historical[-5]) / historical[-5] if len(historical) > 5 else 0
    
    # Score calculation (-1 to 1)
    score = 0
    
    # Trend component
    if trend > 0:
        score += 0.3 * trend_strength
    else:
        score -= 0.3 * trend_strength
    
    # RSI component
    if rsi < 30:  # Oversold
        score += 0.3
    elif rsi > 70:  # Overbought
        score -= 0.3
    
    # MACD component
    if macd > signal:
        score += 0.2
    elif macd < signal:
        score -= 0.2
    
    # Momentum component
    score += momentum * 2
    
    # Volatility adjustment
    if volatility > 0.05:  # High volatility
        score = score * 0.7
    
    # Clip score
    score = np.clip(score, -1, 1)
    
    # Generate signal
    if score > 0.6:
        return "🚀 STRONG BUY", score, f"Strong bullish momentum with RSI {rsi:.0f} and positive MACD"
    elif score > 0.2:
        return "📈 BUY", score, f"Positive trend detected. MA crossover suggests upward movement"
    elif score < -0.6:
        return "🔻 STRONG SELL", abs(score), f"Bearish signals with RSI {rsi:.0f} and negative momentum"
    elif score < -0.2:
        return "📉 SELL", abs(score), f"Downward pressure with weakening indicators"
    else:
        return "⚡ HOLD", abs(score), f"Neutral market conditions. RSI: {rsi:.0f}"

# Simulated price fetching function with realistic data
def fetch_real_price(token, exchange):
    """Fetch price from exchange with realistic simulation"""
    try:
        # Base prices for major tokens (simulated)
        BASE_PRICES = {
            'BTC': 43500, 'ETH': 2280, 'BNB': 310, 'SOL': 95, 'XRP': 0.62, 'ADA': 0.45,
            'DOGE': 0.08, 'AVAX': 35, 'MATIC': 0.85, 'LINK': 15, 'UNI': 6.5, 'AAVE': 85,
            'DOT': 7, 'ATOM': 9, 'NEAR': 3.2, 'FTM': 0.4, 'ALGO': 0.18, 'VET': 0.023,
            'SAND': 0.45, 'MANA': 0.42, 'AXS': 7.2, 'GALA': 0.025, 'ENJ': 0.28,
            'USDT': 1.00, 'USDC': 1.00, 'DAI': 1.00, 'BUSD': 1.00
        }
        
        base_price = BASE_PRICES.get(token, random.uniform(0.1, 100))
        
        # Add exchange-specific premium/discount
        exchange_premium = {
            "CEX - Binance": 0.001,
            "CEX - Coinbase": 0.002,
            "CEX - Kraken": -0.001,
            "CEX - KuCoin": 0.0005,
            "CEX - Bybit": 0.0008,
            "DEX - Uniswap V2": 0.003,
            "DEX - Uniswap V3": 0.002,
            "DEX - SushiSwap": 0.0025,
            "DEX - PancakeSwap V2": -0.002,
            "DEX - PancakeSwap V3": -0.001,
            "DEX - QuickSwap": 0.001,
            "DEX - Raydium": 0.0005
        }
        
        premium = exchange_premium.get(exchange, 0)
        
        # Add random variation
        variation = random.uniform(-0.01, 0.01)
        
        price = base_price * (1 + premium + variation)
        
        # Add small random walk for price history
        if token in st.session_state.price_history and st.session_state.price_history[token]:
            last_price = st.session_state.price_history[token][-1]
            # Make price move realistically
            change = random.uniform(-0.005, 0.005)
            price = last_price * (1 + change)
        
        return price
    except:
        return None

def scan_for_opportunities():
    """Main scanning function with enhanced logic"""
    if not st.session_state.scanning or not st.session_state.selected_tokens or not st.session_state.selected_exchanges:
        return
    
    opportunities = []
    
    for token in st.session_state.selected_tokens:
        prices = {}
        
        # Get prices from all selected exchanges
        for exchange in st.session_state.selected_exchanges:
            price = fetch_real_price(token, exchange)
            if price:
                prices[exchange] = price
        
        # Find arbitrage opportunities
        if len(prices) >= 2:
            # Sort exchanges by price
            sorted_exchanges = sorted(prices.items(), key=lambda x: x[1])
            
            # Check all possible pairs for best opportunity
            for i in range(len(sorted_exchanges)):
                for j in range(i + 1, len(sorted_exchanges)):
                    buy_exchange, buy_price = sorted_exchanges[i]
                    sell_exchange, sell_price = sorted_exchanges[j]
                    
                    # Calculate profit margin
                    gross_profit = ((sell_price - buy_price) / buy_price) * 100
                    
                    # Get exchange fees
                    buy_fee = EXCHANGES.get(buy_exchange, {}).get('fee', 0.002)
                    sell_fee = EXCHANGES.get(sell_exchange, {}).get('fee', 0.002)
                    total_fees = (buy_fee + sell_fee) * 100
                    
                    net_profit = gross_profit - total_fees
                    
                    # Check if profitable
                    if net_profit >= st.session_state.get('min_profit', 0.5):
                        # Calculate confidence based on multiple factors
                        price_spread = (sell_price - buy_price) / buy_price
                        liquidity_score = min(1.0, price_spread * 10)  # Simulated liquidity
                        volatility = 0.03  # Simulated volatility
                        
                        confidence = min(0.95, max(0.3, 
                            (net_profit / 5) * 0.4 + 
                            (1 - volatility) * 0.3 + 
                            liquidity_score * 0.3
                        ))
                        
                        opportunities.append({
                            'token': token,
                            'buy_exchange': buy_exchange,
                            'sell_exchange': sell_exchange,
                            'buy_price': buy_price,
                            'sell_price': sell_price,
                            'profit': net_profit,
                            'confidence': confidence,
                            'timestamp': datetime.now(),
                            'gross_profit': gross_profit,
                            'fees': total_fees
                        })
    
    # Sort by profit
    opportunities.sort(key=lambda x: x['profit'], reverse=True)
    st.session_state.opportunities = opportunities[:50]  # Keep top 50
    
    # Generate alerts for high-profit opportunities
    for opp in opportunities[:5]:
        if opp['profit'] > st.session_state.get('min_profit', 0.5) * 2:
            alert = f"🔥 {opp['token']}: {opp['profit']:.2f}% profit! {opp['buy_exchange']} → {opp['sell_exchange']} | Confidence: {opp['confidence']:.0%}"
            if alert not in st.session_state.alerts[-10:]:
                st.session_state.alerts.append(alert)
                if len(st.session_state.alerts) > 20:
                    st.session_state.alerts.pop(0)

def update_price_history():
    """Update price history for AI predictions"""
    for token in st.session_state.selected_tokens:
        # Get current price from a major exchange
        current_price = fetch_real_price(token, "CEX - Binance")
        
        if current_price:
            if token not in st.session_state.price_history:
                st.session_state.price_history[token] = []
            
            st.session_state.price_history[token].append(current_price)
            
            # Keep last 500 data points
            if len(st.session_state.price_history[token]) > 500:
                st.session_state.price_history[token] = st.session_state.price_history[token][-500:]

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
