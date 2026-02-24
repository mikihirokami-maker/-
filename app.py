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
    .running-box { border: 1px solid #00f2ff; padding: 20px; border-radius: 10px; background-color: #050505; text-align: center; margin-bottom: 20px; }
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
if 'is_running' not in st.session_state: st.session_state.is_running = False

# --- API関数 ---
def get_jst_time():
    JST = timezone(timedelta(hours=9))
    return datetime.now(JST)

def get_threads_user_info(token):
    """トークンから正しいUser IDと名前を取得する"""
    url = "https://graph.threads.net/v1.0/me"
    params = {
        'fields': 'id,username,name',
        'access_token': token
    }
    try:
        res = requests.get(url, params=params).json()
        if 'id' in res:
            return res # {'id': '...', 'username': '...', 'name': '...'}
        else:
            return None
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
    
    if image_obj is not None:
        with st.spinner("画像をサーバーへ転送中..."):
            image_url = upload_image_to_imgur(image_obj)
            if not image_url: return False, "画像のアップロード失敗"

    url_container = f"https://graph.threads.net/v1.0/{user_id}/threads"
    params = {'access_token': token, 'media_type': 'IMAGE' if image_url else 'TEXT'}
    if image_url: params['image_url'] = image_url
    params['text'] = text

    try:
        res = requests.post(url_container, data=params).json()
        
        # エラー処理: トークン切れなら更新して再試行
        if 'error' in res or 'id' not in res:
            # 念のためエラー内容を確認
            print(f"First attempt failed: {res}")
            new_token = refresh_access_token(token)
            if new_token:
                account['token'] = new_token
                save_json(ACCOUNTS_FILE, st.session_state.accounts)
                params['access_token'] = new_token
                res = requests.post(url_container, data=params).json()
        
        if 'id' not in res: return False, f"作成エラー: {res}"
        
        creation_id = res['id']
        url_publish = f"https://graph.threads.net/v1.0/{user_id}/threads_publish"
        pub_params = {'creation_id': creation_id, 'access_token': account['token']}
        pub_res = requests.post(url_publish, data=pub_params).json()
        
        return ('id' in pub_res, f"ID: {pub_res.get('id')}" if 'id' in pub_res else f"公開エラー: {pub_res}")
    except Exception as e:
        return False, str(e)

# --- 🚀 自動化実行画面 (Running Mode) ---
if st.session_state.is_running:
    # ここで画面を描画することで「真っ白」を防ぎます
    st.title("🚀 自動化プロセス実行中")
    
    # 中断ボタン
    col_stop, col_info = st.columns([1, 4])
    with col_stop:
        if st.button("⛔ 処理を強制停止する"):
            st.session_state.is_running = False
            st.rerun()
    with col_info:
        st.info("ブラウザを閉じないでください。ランダム待機時間はここでカウントダウンされます。")

    log_area = st.empty()
    status_box = st.empty()
    progress_bar = st.progress(0)
    
    # 実行リストのコピー
    execution_list = list(st.session_state.storage)
    total_tasks = len(execution_list)
    
    for i, p in enumerate(execution_list):
        # 停止チェック
        if not st.session_state.is_running: break

        progress_bar.progress((i) / total_tasks if total_tasks > 0 else 0)
        
        if p['acc_idx'] >= len(st.session_state.accounts): continue
        acc = st.session_state.accounts[p['acc_idx']]
        
        status_box.markdown(f"""
        <div class="running-box">
            <h3>▶ 処理中 ({i+1}/{total_tasks})</h3>
            <p>アカウント: <b>{acc['name']}</b></p>
        </div>
        """, unsafe_allow_html=True)
        
        # ランダム待機ロジック
        if p['random']:
            s, e = p['time_range']
            if s >= e: e = 24
            now = get_jst_time()
            target_h = random.randint(s, max(s, e-1))
            target_m = random.randint(0, 59)
            target_time = now.replace(hour=target_h, minute=target_m, second=0)
            wait_seconds = int((target_time - now).total_seconds())
            
            if wait_seconds > 0:
                # カウントダウン (1秒ごとに画面更新)
                for remaining in range(wait_seconds, 0, -1):
                    if not st.session_state.is_running: break # 中断チェック
                    
                    status_box.markdown(f"""
                    <div class="running-box" style="border-color: yellow;">
                        <h3>⏳ 待機中</h3>
                        <p>投稿予定時刻: <b>{target_h}:{target_m:02d}</b></p>
                        <h2 style="color: yellow;">あと {remaining} 秒</h2>
                        <p><small>※待たずに投稿したい場合は「強制停止」してランダム設定を外してください</small></p>
                    </div>
                    """, unsafe_allow_html=True)
                    time.sleep(1)
            else:
                status_box.warning("設定時間を過ぎているため、即時投稿します")
                time.sleep(2)
        
        if not st.session_state.is_running: break

        # 投稿実行
        status_box.info(f"📤 {acc['name']} に投稿を送信中...")
        suc, msg = post_to_threads(acc, p['text'], p['image_file'])
        
        now_s = get_jst_time().strftime('%H:%M:%S')
        res_icon = "✅" if suc else "❌"
        log_msg = f"{res_icon} {now_s} [{acc['name']}] {msg}"
        st.session_state.logs.append(log_msg)
        log_area.code("\n".join(reversed(st.session_state.logs)))
        
        time.sleep(1)

    if st.session_state.is_running:
        progress_bar.progress(1.0)
        status_box.success("すべての処理が完了しました！")
        st.balloons()
        
        # 完了処理
        st.session_state.storage = [] # 収納ボックスを空にする
        save_json(STORAGE_FILE, st.session_state.storage)
        
        time.sleep(3)
        st.session_state.is_running = False
        st.rerun()

# --- メイン画面 (通常時) ---
st.title("THREADS AUTO MASTER ♾️")

with st.sidebar:
    st.title("🤖 システム制御")
    st.info(f"🇯🇵 現在時刻 (JST)\n{get_jst_time().strftime('%Y-%m-%d %H:%M:%S')}")
    st.markdown("---")
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

tab1, tab2, tab3 = st.tabs(["① アカウント設定", "② 投稿作成＆自動化", "③ 実行ログ"])

# --- ① アカウント ---
with tab1:
    st.header("アカウント設定 (ID自動取得)")
    st.info("Access Tokenを入力して「自動取得して保存」を押せば、正しいIDが設定されます。")
    
    with st.expander("➕ アカウント追加", expanded=True):
        new_token = st.text_input("Access Token (必須)", type="password")
        new_secret = st.text_input("App Secret (任意)", type="password")
        
        if st.button("🔍 IDを自動取得して保存"):
            if new_token:
                user_info = get_threads_user_info(new_token)
                if user_info:
                    # 取得成功
                    nm = user_info.get('name', 'Unknown')
                    uid = user_info.get('id')
                    username = user_info.get('username')
                    
                    st.session_state.accounts.append({
                        "name": f"{nm} (@{username})", 
                        "id": uid, 
                        "token": new_token, 
                        "secret": new_secret
                    })
                    save_json(ACCOUNTS_FILE, st.session_state.accounts)
                    st.success(f"成功！アカウントを追加しました: {nm} (ID: {uid})")
                else:
                    st.error("情報の取得に失敗しました。トークンが正しいか確認してください。")
            else:
                st.error("トークンを入力してください")
    
    if st.session_state.accounts:
        st.markdown("### 連携中のアカウント")
        for i, acc in enumerate(st.session_state.accounts):
            c_inf, c_del = st.columns([4, 1])
            c_inf.write(f"✅ **{acc['name']}** (ID: {acc['id']})")
            if c_del.button("削除", key=f"d_acc_{i}"):
                st.session_state.accounts.pop(i)
                save_json(ACCOUNTS_FILE, st.session_state.accounts)
                st.rerun()

# --- ② 投稿作成＆自動化 ---
with tab2:
    st.header("投稿ファクトリー")
    
    # --- 収納ボックス ---
    with st.expander("📦 収納ボックス (待機中の投稿)"):
        if not st.session_state.storage:
            st.info("待機中の投稿はありません")
        else:
            for i, p in enumerate(st.session_state.storage):
                acc_name = "不明"
                if 0 <= p['acc_idx'] < len(st.session_state.accounts):
                    acc_name = st.session_state.accounts[p['acc_idx']]['name']
                st.markdown(f"""<div class="storage-box"><b>📦 {acc_name} 用の投稿</b><br>内容: {p['text'][:30]}...</div>""", unsafe_allow_html=True)
                c_res, c_del = st.columns([1, 1])
                if c_res.button(f"↩️ 修正する", key=f"res_{i}"):
                    st.session_state.posts = [p] 
                    st.session_state.storage.pop(i) 
                    save_json(POSTS_FILE, st.session_state.posts)
                    save_json(STORAGE_FILE, st.session_state.storage)
                    st.rerun()
                if c_del.button(f"🗑️ 削除", key=f"del_st_{i}"):
                    st.session_state.storage.pop(i)
                    save_json(STORAGE_FILE, st.session_state.storage)
                    st.rerun()

    st.markdown("---")
    st.subheader("📝 新規作成 / 編集")
    
    if not st.session_state.accounts:
        st.warning("先にアカウントを追加してください")
    else:
        acc_names = [a['name'] for a in st.session_state.accounts]
        post = st.session_state.posts[0]
        
        st.markdown(f"""<div class="post-card">""", unsafe_allow_html=True)
        c1, c2 = st.columns([1, 1])
        with c1:
            if post['acc_idx'] >= len(acc_names): post['acc_idx'] = 0
            post['acc_idx'] = acc_names.index(st.selectbox(f"アカウント選択", acc_names, index=post['acc_idx'], key=f"s_0"))
        with c2:
            post['random'] = st.checkbox(f"ランダム時間を有効化", value=post['random'], key=f"r_0")
            if post['random']:
                s, e = st.slider(f"時間帯設定", 0, 24, post['time_range'], key=f"sl_0")
                post['time_range'] = (s, e)
                st.caption("※指定した時間までブラウザを開いたまま待機します")
        
        c3, c4 = st.columns([1, 1])
        with c3:
            up = st.file_uploader(f"画像 (任意)", type=['png','jpg'], key=f"f_0")
            if up: 
                post['image_file'] = up
                st.image(up, width=150)
        with c4:
            post['text'] = st.text_area(f"投稿本文", value=post['text'], height=100, key=f"t_0")
        st.markdown("</div>", unsafe_allow_html=True)

        save_json(POSTS_FILE, st.session_state.posts)

        st.markdown("---")
        
        if st.button("✅ 完了＆自動化スタート (即時実行)", type="primary"):
            current_post = st.session_state.posts[0]
            if not current_post['text'] and not current_post['image_file']:
                st.error("本文または画像を入力してください")
            else:
                target_acc_idx = current_post['acc_idx']
                # 1. 重複防止削除
                st.session_state.storage = [p for p in st.session_state.storage if p['acc_idx'] != target_acc_idx]
                # 2. 追加
                st.session_state.storage.append(current_post)
                save_json(STORAGE_FILE, st.session_state.storage)
                # 3. リセット
                st.session_state.posts = [{"text": "", "image_file": None, "acc_idx": 0, "random": False, "time_range": (12, 15)}]
                save_json(POSTS_FILE, st.session_state.posts)
                # 4. 実行モードへ
                st.session_state.is_running = True
                st.rerun()

# --- ③ 実行ログ ---
with tab3:
    st.header("実行ログ履歴")
    if st.session_state.logs:
        st.code("\n".join(reversed(st.session_state.logs)))
    else:
        st.info("履歴はありません")
