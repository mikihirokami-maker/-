import streamlit as st
import time
import random
import requests
import json
import os
from datetime import datetime, timedelta, timezone

# --- ページ設定 ---
st.set_page_config(page_title="Threads Auto Master Pro", layout="wide", page_icon="🤖")

# --- デザイン設定 ---
st.markdown("""
<style>
    .stApp { background-color: #000000; color: #00f2ff; }
    h1, h2, h3, h4 { color: #00f2ff !important; font-family: 'Helvetica Neue', sans-serif; }
    .stTextInput, .stTextArea, .stSelectbox, .stTimeInput, .stFileUploader {
        background-color: #111 !important; color: #fff !important; border: 1px solid #333 !important; border-radius: 8px !important;
    }
    .stButton>button {
        background: linear-gradient(90deg, #00c6ff, #0072ff); color: white; font-weight: bold; border: none; border-radius: 8px; padding: 0.5rem 1rem;
    }
    .post-card { background: rgba(255, 255, 255, 0.05); padding: 20px; border-radius: 15px; border: 1px solid #00f2ff; margin-bottom: 20px; }
    .storage-box { background: rgba(0, 255, 0, 0.1); padding: 15px; border-radius: 10px; border: 1px dashed #00ff00; margin-bottom: 10px; }
    img { border-radius: 10px; border: 1px solid #333; margin-top: 10px; }
</style>
""", unsafe_allow_html=True)

# --- データ保存機能 ---
ACCOUNTS_FILE = "accounts.json"
POSTS_FILE = "posts.json"
STORAGE_FILE = "storage.json"

def load_json(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_json(file_path, data):
    serializable_data = []
    for item in data:
        item_copy = item.copy()
        if 'image_file' in item_copy:
            del item_copy['image_file'] 
        serializable_data.append(item_copy)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(serializable_data, f, ensure_ascii=False, indent=2)

# --- セッション初期化 ---
if 'accounts' not in st.session_state: st.session_state.accounts = load_json(ACCOUNTS_FILE)
if 'posts' not in st.session_state:
    loaded = load_json(POSTS_FILE)
    if loaded:
        for p in loaded: p['image_file'] = None
        st.session_state.posts = loaded
    else:
        st.session_state.posts = [{"text": "", "image_file": None, "acc_idx": 0, "random": False, "time_range": (12, 15)}]
if 'storage' not in st.session_state:
    loaded_st = load_json(STORAGE_FILE)
    for p in loaded_st: p['image_file'] = None
    st.session_state.storage = loaded_st
if 'logs' not in st.session_state: st.session_state.logs = []

# --- API関数 ---
def get_jst_time():
    JST = timezone(timedelta(hours=9))
    return datetime.now(JST)

def get_threads_user_info(token):
    """トークンからID自動取得"""
    url = "https://graph.threads.net/v1.0/me"
    params = {'fields': 'id,username,name', 'access_token': token}
    try:
        res = requests.get(url, params=params).json()
        return res if 'id' in res else None
    except:
        return None

def refresh_access_token(token):
    url = "https://graph.threads.net/refresh_access_token"
    params = {'grant_type': 'th_refresh_token', 'access_token': token}
    try:
        res = requests.get(url, params=params).json()
        return res.get('access_token')
    except:
        return None

def upload_image_to_imgur(image_file):
    CLIENT_ID = "d3a6697416345f7" 
    url = "https://api.imgur.com/3/image"
    headers = {"Authorization": f"Client-ID {CLIENT_ID}"}
    try:
        image_data = image_file.getvalue()
        payload = {"image": image_data}
        response = requests.post(url, headers=headers, files=payload)
        data = response.json()
        return data['data']['link'] if data['success'] else None
    except:
        return None

def post_to_threads(account, text, image_obj=None):
    user_id = account['id']
    token = account['token']
    image_url = None
    
    # 1. 画像アップロード
    if image_obj is not None:
        with st.spinner(f"画像を転送中... ({account['name']})"):
            image_url = upload_image_to_imgur(image_obj)
            if not image_url: return False, "画像のアップロード失敗"

    url_container = f"https://graph.threads.net/v1.0/{user_id}/threads"
    params = {'access_token': token, 'media_type': 'IMAGE' if image_url else 'TEXT'}
    if image_url: params['image_url'] = image_url
    params['text'] = text

    try:
        # 2. コンテナ作成
        res = requests.post(url_container, data=params).json()
        
        # エラー処理: トークン更新
        if 'error' in res or 'id' not in res:
            new_token = refresh_access_token(token)
            if new_token:
                account['token'] = new_token
                save_json(ACCOUNTS_FILE, st.session_state.accounts)
                params['access_token'] = new_token
                res = requests.post(url_container, data=params).json()
        
        if 'id' not in res: return False, f"作成エラー: {res}"
        
        creation_id = res['id']
        
        # 3. 【重要】メディア準備待ち (エラー対策)
        # 画像がある場合は特に、Threads側で準備ができるまで待つ必要があります
        if image_url:
            with st.spinner("メディア処理待機中(10秒)... これでエラーを防ぎます"):
                time.sleep(10)
        else:
            time.sleep(2)

        # 4. 公開 (Publish)
        url_publish = f"https://graph.threads.net/v1.0/{user_id}/threads_publish"
        pub_params = {'creation_id': creation_id, 'access_token': account['token']}
        pub_res = requests.post(url_publish, data=pub_params).json()
        
        return ('id' in pub_res, f"ID: {pub_res.get('id')}" if 'id' in pub_res else f"公開エラー: {pub_res}")
    except Exception as e:
        return False, str(e)

# --- メイン画面 ---
st.title("THREADS AUTO MASTER ♾️")

with st.sidebar:
    st.title("🤖 システム制御")
    st.info(f"🇯🇵 {get_jst_time().strftime('%H:%M:%S')}")
    if st.button("全トークン強制更新"):
        c = 0
        for acc in st.session_state.accounts:
            new_t = refresh_access_token(acc['token'])
            if new_t:
                acc['token'] = new_t
                c += 1
        if c > 0:
            save_json(ACCOUNTS_FILE, st.session_state.accounts)
            st.success(f"{c}件更新完了")
    if st.button("ログクリア"): st.session_state.logs = []

tab1, tab2, tab3 = st.tabs(["① アカウント", "② 投稿作成＆リスト", "③ 実行ログ"])

# --- ① アカウント ---
with tab1:
    st.header("アカウント設定")
    with st.expander("➕ アカウント追加", expanded=True):
        new_token = st.text_input("Access Token", type="password")
        new_secret = st.text_input("App Secret (任意)", type="password")
        if st.button("🔍 ID自動取得 & 保存"):
            if new_token:
                info = get_threads_user_info(new_token)
                if info:
                    st.session_state.accounts.append({
                        "name": f"{info.get('name')} (@{info.get('username')})", 
                        "id": info.get('id'), "token": new_token, "secret": new_secret
                    })
                    save_json(ACCOUNTS_FILE, st.session_state.accounts)
                    st.success(f"追加: {info.get('name')}")
                    st.rerun()
                else: st.error("取得失敗。トークンを確認してください")
    
    if st.session_state.accounts:
        for i, acc in enumerate(st.session_state.accounts):
            c1, c2 = st.columns([4, 1])
            c1.write(f"✅ **{acc['name']}**")
            if c2.button("削除", key=f"d{i}"):
                st.session_state.accounts.pop(i)
                save_json(ACCOUNTS_FILE, st.session_state.accounts)
                st.rerun()

# --- ② 投稿作成＆リスト ---
with tab2:
    # --- 作成エリア ---
    st.subheader("📝 投稿を作成")
    if not st.session_state.accounts:
        st.warning("アカウントを追加してください")
    else:
        acc_names = [a['name'] for a in st.session_state.accounts]
        post = st.session_state.posts[0]
        
        st.markdown(f"""<div class="post-card">""", unsafe_allow_html=True)
        c1, c2 = st.columns([1, 1])
        with c1:
            if post['acc_idx'] >= len(acc_names): post['acc_idx'] = 0
            post['acc_idx'] = acc_names.index(st.selectbox("アカウント", acc_names, index=post['acc_idx'], key="s0"))
        with c2:
            post['random'] = st.checkbox("ランダム時間を設定", value=post['random'], key="r0")
            if post['random']:
                s, e = st.slider("時間帯", 0, 24, post['time_range'], key="sl0")
                post['time_range'] = (s, e)
        
        c3, c4 = st.columns([1, 1])
        with c3:
            up = st.file_uploader("画像 (任意)", type=['png','jpg'], key="f0")
            if up: post['image_file'] = up; st.image(up, width=100)
        with c4:
            post['text'] = st.text_area("本文", value=post['text'], height=100, key="t0")
        st.markdown("</div>", unsafe_allow_html=True)
        
        # 保存ボタン
        if st.button("✅ 保存して次へ (リストに追加)", type="primary"):
            cur = st.session_state.posts[0]
            if not cur['text'] and not cur['image_file']:
                st.error("内容が空です")
            else:
                tid = cur['acc_idx']
                # 重複削除
                st.session_state.storage = [p for p in st.session_state.storage if p['acc_idx'] != tid]
                # 追加
                st.session_state.storage.append(cur)
                save_json(STORAGE_FILE, st.session_state.storage)
                # リセット
                st.session_state.posts = [{"text": "", "image_file": None, "acc_idx": 0, "random": False, "time_range": (12, 15)}]
                save_json(POSTS_FILE, st.session_state.posts)
                st.toast("リストに追加しました！次の投稿を作成できます")
                time.sleep(0.5)
                st.rerun()

    st.markdown("---")

    # --- 待機リスト & 実行ボタン ---
    st.subheader(f"🚀 待機リスト (計 {len(st.session_state.storage)} 件)")
    
    # 実行オプション
    col_exec, col_opt = st.columns([2, 1])
    with col_opt:
        skip_wait = st.checkbox("⚡ 待ち時間を無視して即時実行", value=True, help="チェックを入れると設定した時間を無視して今すぐ投稿します")
    
    with col_exec:
        if st.button("🚀 待機中の投稿をすべて放出する", type="primary", use_container_width=True):
            if not st.session_state.storage:
                st.error("待機中の投稿がありません")
            else:
                exec_list = list(st.session_state.storage)
                progress = st.progress(0)
                status = st.empty()
                
                for i, p in enumerate(exec_list):
                    acc = st.session_state.accounts[p['acc_idx']]
                    status.info(f"処理中: {acc['name']} ...")
                    
                    # 待機処理 (スキップ可能)
                    if p['random'] and not skip_wait:
                        s, e = p['time_range']
                        if s >= e: e = 24
                        now = get_jst_time()
                        target_h = random.randint(s, max(s, e-1))
                        target_m = random.randint(0, 59)
                        target = now.replace(hour=target_h, minute=target_m, second=0)
                        wait = (target - now).total_seconds()
                        
                        if wait > 0:
                            status.warning(f"⏳ {acc['name']}: {target_h}:{target_m} まで待機中 ({int(wait)}秒)...")
                            time.sleep(wait)
                    
                    # 投稿実行
                    suc, msg = post_to_threads(acc, p['text'], p['image_file'])
                    
                    now_s = get_jst_time().strftime('%H:%M:%S')
                    icon = "✅" if suc else "❌"
                    st.session_state.logs.append(f"{icon} {now_s} [{acc['name']}] {msg}")
                    progress.progress((i + 1) / len(exec_list))
                
                # 完了後クリア
                st.session_state.storage = []
                save_json(STORAGE_FILE, st.session_state.storage)
                status.success("全処理完了！")
                st.balloons()
                time.sleep(2)
                st.rerun()

    # リスト表示
    for i, p in enumerate(st.session_state.storage):
        aname = st.session_state.accounts[p['acc_idx']]['name']
        st.info(f"📦 {aname}: {p['text'][:20]}...")

# --- ③ ログ ---
with tab3:
    if st.session_state.logs:
        st.code("\n".join(reversed(st.session_state.logs)))
    else: st.info("履歴なし")
