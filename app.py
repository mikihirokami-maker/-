import streamlit as st
import time
import random
import requests
from datetime import datetime, timedelta
import pandas as pd

# --- ページ設定 ---
st.set_page_config(page_title="Threads Auto Master Pro", layout="wide", page_icon="🤖")

# --- デザイン設定 ---
st.markdown("""
<style>
    .stApp { background-color: #000000; color: #00f2ff; }
    h1, h2, h3, h4 { color: #00f2ff !important; font-family: 'Helvetica Neue', sans-serif; }
    .stTextInput, .stTextArea, .stSelectbox { background-color: #111 !important; color: #fff !important; border: 1px solid #333 !important; }
    .stButton>button { background: linear-gradient(90deg, #00c6ff, #0072ff); color: white; font-weight: bold; border: none; border-radius: 8px; }
    .post-card { background: rgba(255, 255, 255, 0.05); padding: 20px; border-radius: 15px; border: 1px solid #00f2ff; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

# --- セッション初期化 ---
if 'accounts' not in st.session_state:
    st.session_state.accounts = []
if 'posts' not in st.session_state:
    st.session_state.posts = []
if 'logs' not in st.session_state:
    st.session_state.logs = []

# --- API関数 (リフレッシュ機能付き) ---
def refresh_access_token(token):
    """トークンの有効期限を延長する"""
    url = "https://graph.threads.net/refresh_access_token"
    params = {
        'grant_type': 'th_refresh_token',
        'access_token': token
    }
    try:
        res = requests.get(url, params=params).json()
        if 'access_token' in res:
            return res['access_token']
        else:
            return None
    except:
        return None

def post_to_threads(account, text, image_url=None):
    """投稿実行関数"""
    user_id = account['id']
    token = account['token']
    
    # 投稿前にトークンリフレッシュを試みる（簡易実装）
    # ※本来は期限切れが近い時だけやりますが、念のため毎回チェック等のロジックも可能です
    # ここではシンプルにそのまま投稿します
    
    url_container = f"https://graph.threads.net/v1.0/{user_id}/threads"
    params = {
        'access_token': token,
        'media_type': 'IMAGE' if image_url else 'TEXT'
    }
    
    if image_url:
        params['image_url'] = image_url
        params['text'] = text
    else:
        params['text'] = text

    try:
        # 1. コンテナ作成
        res = requests.post(url_container, data=params).json()
        if 'id' not in res:
            # エラーの場合、トークン切れの可能性があるのでリフレッシュを試みて再挑戦
            new_token = refresh_access_token(token)
            if new_token:
                account['token'] = new_token # 新しいトークンを保存
                params['access_token'] = new_token
                res = requests.post(url_container, data=params).json() # 再挑戦
            
            if 'id' not in res:
                return False, f"エラー(作成): {res}"
        
        creation_id = res['id']
        
        # 2. 公開
        url_publish = f"https://graph.threads.net/v1.0/{user_id}/threads_publish"
        pub_params = {'creation_id': creation_id, 'access_token': account['token']}
        pub_res = requests.post(url_publish, data=pub_params).json()
        
        if 'id' in pub_res:
            return True, f"投稿成功ID: {pub_res['id']}"
        else:
            return False, f"エラー(公開): {pub_res}"
            
    except Exception as e:
        return False, str(e)

# --- サイドバー ---
with st.sidebar:
    st.title("🤖 システム制御")
    st.write(f"現在時刻: {datetime.now().strftime('%H:%M:%S')}")
    if st.button("全トークンを強制更新"):
        for acc in st.session_state.accounts:
            new_t = refresh_access_token(acc['token'])
            if new_t:
                acc['token'] = new_t
                st.success(f"{acc['name']} のトークンを更新しました")
            else:
                st.error(f"{acc['name']} の更新失敗")

# --- メイン画面 ---
st.title("THREADS AUTO MASTER ♾️ (Permanent Ver.)")

tab1, tab2, tab3 = st.tabs(["① アカウント設定 (永久化)", "② 投稿作成", "③ 自動化実行"])

# --- ① アカウント設定 ---
with tab1:
    st.header("アカウント連携設定")
    st.info("App Secretを入力しなくても動きますが、期限切れ防止のため入力推奨です。")
    
    with st.expander("➕ アカウント追加", expanded=True):
        c1, c2 = st.columns(2)
        new_name = c1.text_input("アカウント名", key="n_name")
        new_id = c2.text_input("User ID", key="n_id", type="password")
        new_token = st.text_input("Access Token (必須)", key="n_token", type="password")
        # App Secretは必須ではないが、あると便利
        # new_secret = st.text_input("App Secret (任意:自動更新用)", key="n_secret", type="password") 
        
        if st.button("アカウント保存"):
            if new_name and new_id and new_token:
                st.session_state.accounts.append({
                    "name": new_name,
                    "id": new_id,
                    "token": new_token
                    # "secret": new_secret
                })
                st.success(f"保存完了: {new_name}")
            else:
                st.error("必須項目を入力してください")
    
    # リスト表示
    for acc in st.session_state.accounts:
        st.write(f"✅ **{acc['name']}** (ID: {acc['id'][:4]}...) - 連携済み")

# --- ② 投稿作成 ---
with tab2:
    st.header("投稿スケジューラー")
    if st.button("➕ 投稿枠を追加"):
        st.session_state.posts.append({"text": "", "image": "", "acc_idx": 0, "random": False})
    
    if not st.session_state.accounts:
        st.warning("先にアカウントを追加してください")
    else:
        acc_list = [a['name'] for a in st.session_state.accounts]
        for i, post in enumerate(st.session_state.posts):
            st.markdown(f"""<div class="post-card"><h4>投稿 #{i+1}</h4>""", unsafe_allow_html=True)
            c1, c2 = st.columns([1, 2])
            with c1:
                post['acc_idx'] = acc_list.index(st.selectbox(f"アカウント #{i+1}", acc_list, key=f"s_{i}"))
                post['random'] = st.checkbox(f"ランダム投稿 #{i+1}", key=f"r_{i}")
            with c2:
                post['text'] = st.text_area(f"内容 #{i+1}", key=f"t_{i}")
                post['image'] = st.text_input(f"画像URL #{i+1}", key=f"img_{i}")
            
            if st.button(f"削除 #{i+1}", key=f"d_{i}"):
                st.session_state.posts.pop(i)
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

# --- ③ 自動化実行 ---
with tab3:
    st.header("自動化モニター")
    if st.button("🚀 自動化スタート", type="primary"):
        st.toast("開始しました")
        log_box = st.empty()
        
        for i, post in enumerate(st.session_state.posts):
            acc = st.session_state.accounts[post['acc_idx']]
            if not post['text'] and not post['image']: continue
            
            if post['random']:
                wait = random.randint(1, 10) # デモ用:1〜10秒
                st.info(f"投稿 #{i+1}: ランダム待機中 ({wait}秒)...")
                time.sleep(wait)
            
            success, msg = post_to_threads(acc, post['text'], post['image'])
            
            now = datetime.now().strftime('%H:%M:%S')
            if success:
                st.session_state.logs.append(f"✅ {now} [{acc['name']}] 成功")
            else:
                st.session_state.logs.append(f"❌ {now} [{acc['name']}] 失敗: {msg}")
            
            # ログ更新
            log_txt = ""
            for l in reversed(st.session_state.logs):
                log_txt += l + "\n"
            log_box.code(log_txt)
        
        st.success("全ての処理が完了しました")
