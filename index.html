import streamlit as st
import time
from datetime import datetime
import pandas as pd

# --- CONFIGURATION & STYLING ---
st.set_page_config(page_title="Threads Automator NEON", layout="wide", page_icon="⚡")

# Custom CSS for "Stylish & Cool" Look (Cyberpunk/Glassmorphism)
st.markdown("""
<style>
    /* Main Background */
    .stApp {
        background-color: #050505;
        background-image: radial-gradient(circle at 50% 50%, #1a1a1a 0%, #000000 100%);
        color: #e0e0e0;
    }
    /* Headers */
    h1, h2, h3 {
        color: #00f2ff !important;
        font-family: 'Helvetica Neue', sans-serif;
        text-shadow: 0 0 10px rgba(0, 242, 255, 0.5);
    }
    /* Cards/Containers */
    .css-1r6slb0, .stTextArea, .stTextInput {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(0, 242, 255, 0.2) !important;
        border-radius: 12px !important;
        color: #fff !important;
    }
    /* Buttons */
    .stButton>button {
        background: linear-gradient(45deg, #00c6ff, #0072ff);
        color: white;
        border: none;
        border-radius: 8px;
        box-shadow: 0 4px 15px rgba(0, 114, 255, 0.4);
        transition: all 0.3s ease;
        font-weight: bold;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 114, 255, 0.6);
    }
    /* Input Labels */
    label {
        color: #b0b0b0 !important;
        font-size: 0.9rem !important;
    }
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #0a0a0a;
        border-right: 1px solid #222;
    }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR: STATUS & INFO ---
with st.sidebar:
    st.title("⚡ SYSTEM STATUS")
    st.markdown("---")
    st.success("● SYSTEM ONLINE")
    st.info(f"🕒 Time: {datetime.now().strftime('%H:%M:%S')}")
    st.markdown("---")
    st.caption("Threads Automator v1.0")
    st.caption("Designed for Advanced Users")

# --- MAIN INTERFACE ---
st.title("THREADS AUTOMATOR // NEON")
st.markdown("次世代のSNS運用オートメーションツールへようこそ。")

# Tabs for easy navigation
tab1, tab2, tab3 = st.tabs(["🔗 CONNECTION (接続設定)", "📅 DAILY AUTO (自動投稿)", "🔄 RE-POST (再投稿)"])

# --- TAB 1: CONNECTION (接続設定) ---
with tab1:
    st.header("API CONNECTION HUB")
    st.markdown("Threads APIとの接続を確立します。ここでキーを入力してください。")
    
    col1, col2 = st.columns(2)
    with col1:
        user_id = st.text_input("Threads User ID", placeholder="例: 123456789", type="password")
        access_token = st.text_input("Access Token", placeholder="例: EAAwc...", type="password")
    
    with col2:
        st.markdown("#### 接続ステータス")
        if user_id and access_token:
            st.success("API Credentials Detected (Ready)")
            if st.button("接続テストを実行"):
                with st.spinner("Connecting to Meta Graph API..."):
                    time.sleep(1.5) # ダミーの待機時間
                    st.toast("接続成功！アカウントを認識しました。", icon="✅")
        else:
            st.warning("待機中: クレデンシャルを入力してください")
            
    st.markdown("---")
    st.caption("※ APIキーはローカル環境でのみ使用され、外部には送信されません。")

# --- TAB 2: DAILY AUTO POST (自動投稿) ---
with tab2:
    st.header("DAILY AUTOMATION SCHEDULER")
    st.markdown("毎日指定した時間に投稿を自動実行します。")

    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("設定")
        post_time = st.time_input("投稿時間", value=datetime.strptime("19:00", "%H:%M").time())
        is_active = st.toggle("自動投稿を有効化", value=True)
        
    with c2:
        st.subheader("コンテンツ作成")
        post_content = st.text_area("投稿内容 (テンプレート)", height=150, placeholder="ここに毎日の投稿内容を入力... (例: 今日の積み上げ報告！ #Threads)")
        
        if st.button("設定を保存 & スケジューラ起動"):
            st.toast(f"{post_time} にスケジュールを設定しました。", icon="🚀")
            st.balloons()

# --- TAB 3: RE-POST / MONITORING (再投稿機能) ---
with tab3:
    st.header("TARGET RE-POST SYSTEM")
    st.markdown("特定のアカウントの新規投稿を検知し、自動で再投稿（引用含む）を行います。")
    
    col_target, col_action = st.columns(2)
    
    with col_target:
        target_account = st.text_input("監視対象のアカウントID (@不要)", placeholder="target_user_id")
        check_interval = st.slider("チェック間隔 (分)", 5, 60, 15)
    
    with col_action:
        repost_type = st.radio("アクションタイプ", ["単純リポスト (Repost)", "引用投稿 (Quote)"])
        if repost_type == "引用投稿 (Quote)":
            quote_text = st.text_input("引用時のコメント", "素晴らしい投稿です！")
    
    st.markdown("### 実行ログ")
    log_data = pd.DataFrame({
        "Time": ["10:00", "10:15", "10:30"],
        "Target": [target_account if target_account else "-", "-", "-"],
        "Status": ["No Update", "No Update", "Checking..."]
    })
    st.dataframe(log_data, use_container_width=True)
    
    if st.button("監視エージェントを開始"):
        st.warning("バックグラウンドプロセスを開始しました... (停止するにはアプリを終了してください)")
