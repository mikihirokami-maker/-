import streamlit as st
import time
from datetime import datetime
import pandas as pd
import requests  # 通信用のライブラリを追加

# --- CONFIGURATION & STYLING ---
st.set_page_config(page_title="Threads Automator NEON", layout="wide", page_icon="⚡")

# デザイン設定（ここはそのまま）
st.markdown("""
<style>
    .stApp { background-color: #050505; color: #e0e0e0; }
    h1, h2, h3 { color: #00f2ff !important; text-shadow: 0 0 10px rgba(0, 242, 255, 0.5); }
    .stButton>button { background: linear-gradient(45deg, #00c6ff, #0072ff); color: white; border-radius: 8px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- THREADS API FUNCTIONS (本番用) ---
def post_to_threads(user_id, token, text):
    """実際にThreadsに投稿する関数"""
    url = f"https://graph.threads.net/v1.0/{user_id}/threads"
    params = {'text': text, 'access_token': token, 'media_type': 'TEXT'}
    try:
        response = requests.post(url, data=params)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

# --- MAIN INTERFACE ---
st.title("THREADS AUTOMATOR // NEON")

tab1, tab2, tab3 = st.tabs(["🔗 CONNECTION", "📅 DAILY AUTO", "🔄 RE-POST"])

with tab1:
    st.header("API CONNECTION")
    user_id = st.text_input("Threads User ID", type="password")
    access_token = st.text_input("Access Token", type="password")
    
    if st.button("本番接続テスト"):
        if user_id and access_token:
            # 試しに「System Online」と投稿してみるテスト
            res = post_to_threads(user_id, access_token, "System Online ⚡")
            if "id" in res:
                st.success(f"接続＆テスト投稿成功！ ID: {res['id']}")
            else:
                st.error(f"接続失敗: {res}")
        else:
            st.warning("IDとトークンを入れてください")

with tab2:
    st.header("DAILY AUTO POST")
    post_content = st.text_area("投稿内容")
    if st.button("今すぐテスト投稿"):
        res = post_to_threads(user_id, access_token, post_content)
        if "id" in res:
            st.toast("投稿完了！", icon="✅")
        else:
            st.error(f"エラー: {res}")

# (タブ3の再投稿機能は、特定アカウントの投稿を取得するAPI権限が必要なため、まずはここから)
