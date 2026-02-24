import streamlit as st
import time
from datetime import datetime
import pandas as pd
import requests

# --- CONFIGURATION & STYLING ---
st.set_page_config(page_title="Threads Automator NEON", layout="wide", page_icon="⚡")

# デザイン設定
st.markdown("""
<style>
    .stApp {
        background-color: #050505;
        background-image: radial-gradient(circle at 50% 50%, #1a1a1a 0%, #000000 100%);
        color: #e0e0e0;
    }
    h1, h2, h3 {
        color: #00f2ff !important;
        text-shadow: 0 0 10px rgba(0, 242, 255, 0.5);
    }
    .stTextArea, .stTextInput {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(0, 242, 255, 0.2) !important;
        border-radius: 12px !important;
        color: #fff !important;
    }
    .stButton>button {
        background: linear-gradient(45deg, #00c6ff, #0072ff);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- THREADS API FUNCTIONS ---
def post_to_threads(user_id, token, text):
    """Threadsへ実際に投稿を送信する"""
    # 1. コンテナの作成
    base_url = f"https://graph.threads.net/v1.0/{user_id}/threads"
    post_params = {
        'text': text,
        'access_token': token,
        'media_type': 'TEXT'
    }
    try:
        response = requests.post(base_url, data=post_params)
        res_data = response.json()
        
        if "id" in res_data:
            # 2. 公開（パブリッシュ）
            creation_id = res_data["id"]
            publish_url = f"https://graph.threads.net/v1.0/{user_id}/threads_publish"
            publish_params = {
                'creation_id': creation_id,
                'access_token': token
            }
            pub_res = requests.post(publish_url, data=publish_params)
            return pub_res.json()
        else:
            return res_data
    except Exception as e:
        return {"error": str(e)}

# --- SIDEBAR ---
with st.sidebar:
    st.title("⚡ SYSTEM STATUS")
    st.success("● SYSTEM ONLINE")
    st.info(f"🕒 {datetime.now().strftime('%H:%M:%S')}")

# --- MAIN INTERFACE ---
st.title("THREADS AUTOMATOR // NEON")

tab1, tab2, tab3 = st.tabs(["🔗 CONNECTION", "📅 DAILY AUTO", "🔄 RE-POST"])

with tab1:
    st.header("API CONNECTION HUB")
    st.markdown("本物の Threads API トークンを入力してください。")
    u_id = st.text_input("Threads User ID", type="password")
    token = st.text_input("Access Token", type="password")
    
    if st.button("本番接続テスト投稿"):
        if u_id and token:
            with st.spinner("Threadsへ通信中..."):
                res = post_to_threads(u_id, token, "System Online ⚡ #ThreadsAPI")
                if "id" in res:
                    st.success("大成功！Threadsに『System Online ⚡』と投稿されました！")
                else:
                    st.error(f"失敗しました: {res}")
        else:
            st.warning("IDとトークンを入力してください")

with tab2:
    st.header("DAILY AUTOMATION")
    post_content = st.text_area("投稿内容を入力", placeholder="ここに書いた内容がThreadsに飛びます")
    if st.button("今すぐThreadsに投稿する"):
        if u_id and token and post_content:
            res = post_to_threads(u_id, token, post_content)
            if "id" in res:
                st.balloons()
                st.toast("投稿が完了しました！", icon="✅")
            else:
                st.error(f"エラー発生: {res}")
        else:
            st.error("設定または内容が足りません")

with tab3:
    st.header("RE-POST SYSTEM")
    st.info("この機能は現在開発中です。")
