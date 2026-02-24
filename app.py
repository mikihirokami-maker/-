import streamlit as st
import time
import random
import requests
import base64
from datetime import datetime, timedelta
import pandas as pd

# --- ページ設定 ---
st.set_page_config(page_title="Threads Auto Master Pro", layout="wide", page_icon="🤖")

# --- デザイン設定 (Cyberpunk Style) ---
st.markdown("""
<style>
    .stApp {
        background-color: #000000;
        color: #00f2ff;
    }
    h1, h2, h3, h4 {
        color: #00f2ff !important;
        text-shadow: 0 0 10px rgba(0, 242, 255, 0.5);
        font-family: 'Helvetica Neue', sans-serif;
    }
    .stTextInput, .stTextArea, .stSelectbox, .stTimeInput, .stFileUploader {
        background-color: #111 !important;
        color: #fff !important;
        border: 1px solid #333 !important;
        border-radius: 8px !important;
    }
    .stButton>button {
        background: linear-gradient(90deg, #00c6ff, #0072ff);
        color: white;
        font-weight: bold;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        transform: scale(1.02);
        box-shadow: 0 0 15px rgba(0, 114, 255, 0.8);
    }
    /* カード風デザイン */
    .post-card {
        background: rgba(255, 255, 255, 0.05);
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #00f2ff;
        margin-bottom: 20px;
    }
    img {
        border-radius: 10px;
        border: 1px solid #333;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- セッション状態の初期化 ---
if 'accounts' not in st.session_state:
    st.session_state.accounts = []
if 'posts' not in st.session_state:
    st.session_state.posts = []
if 'logs' not in st.session_state:
    st.session_state.logs = []

# --- API関数 ---
def refresh_access_token(token):
    """トークンリフレッシュ"""
    url = "https://graph.threads.net/refresh_access_token"
    params = {'grant_type': 'th_refresh_token', 'access_token': token}
    try:
        res = requests.get(url, params=params).json()
        return res.get('access_token')
    except:
        return None

def upload_image_to_imgur(image_file):
    """画像をImgurにアップロードしてURLを取得する"""
    # ImgurのフリーAPIを使用 (Client-IDはデモ用パブリックキー)
    CLIENT_ID = "d3a6697416345f7" 
    url = "https://api.imgur.com/3/image"
    headers = {"Authorization": f"Client-ID {CLIENT_ID}"}
    
    try:
        image_data = image_file.getvalue()
        payload = {"image": image_data}
        response = requests.post(url, headers=headers, files=payload)
        data = response.json()
        if data['success']:
            return data['data']['link'] # 成功したらURLを返す
        else:
            return None
    except Exception as e:
        return None

def post_to_threads(account, text, image_obj=None):
    """Threadsへ投稿 (ファイルがある場合は自動アップロード)"""
    user_id = account['id']
    token = account['token']
    
    image_url = None
    
    # 画像ファイルがアップロードされている場合、URLに変換する
    if image_obj is not None:
        with st.spinner("画像をサーバーへ転送中..."):
            uploaded_url = upload_image_to_imgur(image_obj)
            if uploaded_url:
                image_url = uploaded_url
            else:
                return False, "画像のアップロードに失敗しました"

    # 1. コンテナ作成
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
        # 初回トライ
        res = requests.post(url_container, data=params).json()
        
        # エラーならリフレッシュして再挑戦
        if 'id' not in res:
            new_token = refresh_access_token(token)
            if new_token:
                account['token'] = new_token 
                params['access_token'] = new_token
                res = requests.post(url_container, data=params).json()
        
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
    st.success("システム稼働中")
    st.write(f"現在時刻: {datetime.now().strftime('%H:%M:%S')}")
    st.markdown("---")
    if st.button("全トークンを強制更新"):
        count = 0
        for acc in st.session_state.accounts:
            if refresh_access_token(acc['token']): count += 1
        st.success(f"{count}件更新完了")
    st.markdown("---")
    if st.button("ログをクリア"):
        st.session_state.logs = []

# --- メイン画面 ---
st.title("THREADS AUTO MASTER ♾️")

tab1, tab2, tab3 = st.tabs(["① アカウント設定", "② 投稿内容・時間設定", "③ 自動化実行"])

# --- ① アカウント設定 ---
with tab1:
    st.header("アカウント連携設定")
    with st.expander("➕ アカウント追加", expanded=True):
        c1, c2 = st.columns(2)
        new_name = c1.text_input("アカウント名", key="n_name")
        new_id = c2.text_input("User ID", key="n_id", type="password")
        new_secret = st.text_input("App Secret (任意)", key="n_secret", type="password")
        new_token = st.text_input("Access Token (必須)", key="n_token", type="password")
        
        if st.button("アカウント保存"):
            if new_name and new_id and new_token:
                st.session_state.accounts.append({
                    "name": new_name, "id": new_id, "token": new_token, "secret": new_secret
                })
                st.success(f"保存完了: {new_name}")
            else:
                st.error("必須項目を入力してください")

    if st.session_state.accounts:
        for acc in st.session_state.accounts:
            st.write(f"✅ **{acc['name']}** (ID: {acc['id'][:4]}...)")

# --- ② 投稿内容・時間設定 ---
with tab2:
    st.header("投稿スケジューラー")
    if st.button("➕ 投稿枠を追加"):
        st.session_state.posts.append({
            "text": "", "image_file": None, "acc_idx": 0, "random": False, "time_range": (12, 15)
        })
    
    if not st.session_state.accounts:
        st.warning("先にアカウントを追加してください")
    else:
        acc_list = [a['name'] for a in st.session_state.accounts]
        for i, post in enumerate(st.session_state.posts):
            st.markdown(f"""<div class="post-card"><h4>投稿 #{i+1}</h4>""", unsafe_allow_html=True)
            
            c1, c2 = st.columns([1, 1])
            with c1:
                post['acc_idx'] = acc_list.index(st.selectbox(f"アカウント #{i+1}", acc_list, key=f"s_{i}"))
            with c2:
                post['random'] = st.checkbox(f"ランダム時間を有効にする #{i+1}", key=f"r_{i}")
                if post['random']:
                    start_h, end_h = st.slider(f"⏰ 時間帯 (#{i+1})", 0, 24, (9, 18), key=f"slider_{i}")
                    post['time_range'] = (start_h, end_h)
                    st.caption(f"{start_h}:00 〜 {end_h}:00 の間で投稿")
                else:
                    st.caption("即時投稿")

            c3, c4 = st.columns([1, 1])
            with c3:
                # ファイルアップローダーに変更！
                uploaded = st.file_uploader(f"画像を選択 (#{i+1})", type=['png', 'jpg', 'jpeg'], key=f"file_{i}")
                if uploaded:
                    post['image_file'] = uploaded
                    st.image(uploaded, caption="プレビュー", width=200)
                else:
                    post['image_file'] = None

            with c4:
                post['text'] = st.text_area(f"投稿内容 #{i+1}", value=post['text'], height=150, key=f"t_{i}")
            
            if st.button(f"🗑️ 削除 #{i+1}", key=f"d_{i}"):
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
            if not post['text'] and not post['image_file']: continue
            
            if post['random']:
                start_h, end_h = post['time_range']
                now = datetime.now()
                if start_h >= end_h: end_h = 24
                
                target_hour = random.randint(start_h, max(start_h, end_h - 1))
                target_minute = random.randint(0, 59)
                target_time = now.replace(hour=target_hour, minute=target_minute, second=0)
                wait_seconds = (target_time - now).total_seconds()
                
                if wait_seconds > 0:
                    st.info(f"投稿 #{i+1}: {target_hour}:{target_minute:02d} に投稿予定... ({int(wait_seconds)}秒待機)")
                    time.sleep(wait_seconds)
                else:
                    st.warning(f"投稿 #{i+1}: 時間を過ぎているため即時投稿します")
                    time.sleep(3)
            
            # 画像ファイルオブジェクトを渡す
            success, msg = post_to_threads(acc, post['text'], post['image_file'])
            
            now_str = datetime.now().strftime('%H:%M:%S')
            if success:
                st.session_state.logs.append(f"✅ {now_str} [{acc['name']}] 成功")
            else:
                st.session_state.logs.append(f"❌ {now_str} [{acc['name']}] 失敗: {msg}")
            
            log_txt = ""
            for l in reversed(st.session_state.logs):
                log_txt += l + "\n"
            log_box.code(log_txt)
        
        st.success("完了しました")
