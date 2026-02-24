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
    .running-box { background: rgba(0, 0, 255, 0.1); padding: 20px; border-radius: 10px; border: 1px solid #00f2ff; text-align: center; margin: 20px 0; }
    img { border-radius: 10px; border: 1px solid #333; margin-top: 10px; }
</style>
""", unsafe_allow_html=True)

# --- データの保存・読み込み機能 ---
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
if 'is_running' not in st.session_state: st.session_state.is_running = False # 自動化実行中フラグ

# --- ユーティリティ関数 ---
def get_jst_time():
    JST = timezone(timedelta(hours=9))
    return datetime.now(JST)

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
        if 'id' not in res:
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

# --- 自動化実行ロジック (別画面で処理) ---
if st.session_state.is_running:
    st.title("🚀 自動化プロセス実行中")
    st.info("ブラウザを閉じずにそのままお待ちください...")
    
    log_area = st.empty()
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # 実行リストのコピー
    execution_list = list(st.session_state.storage)
    total_tasks = len(execution_list)
    
    for i, p in enumerate(execution_list):
        progress_bar.progress((i) / total_tasks if total_tasks > 0 else 0)
        
        if p['acc_idx'] >= len(st.session_state.accounts): continue
        acc = st.session_state.accounts[p['acc_idx']]
        
        status_text.markdown(f"### ▶ 処理中 ({i+1}/{total_tasks}): {acc['name']}")
        
        # ランダム待機ロジック (カウントダウン表示)
        if p['random']:
            s, e = p['time_range']
            if s >= e: e = 24
            now = get_jst_time()
            target_h = random.randint(s, max(s, e-1))
            target_m = random.randint(0, 59)
            target_time = now.replace(hour=target_h, minute=target_m, second=0)
            wait_seconds = int((target_time - now).total_seconds())
            
            if wait_seconds > 0:
                # カウントダウンループ (画面が白くならないように小刻みに更新)
                for remaining in range(wait_seconds, 0, -1):
                    status_text.warning(f"⏳ **待機中**: {target_h}:{target_m} に投稿します\n\nあと **{remaining}** 秒...")
                    time.sleep(1)
            else:
                status_text.warning("時間が過ぎているため、即時投稿します")
                time.sleep(2)
        
        status_text.info(f"📤 {acc['name']} に投稿を送信中...")
        suc, msg = post_to_threads(acc, p['text'], p['image_file'])
        
        now_s = get_jst_time().strftime('%H:%M:%S')
        res_icon = "✅" if suc else "❌"
        log_msg = f"{res_icon} {now_s} [{acc['name']}] {msg}"
        st.session_state.logs.append(log_msg)
        log_area.code("\n".join(reversed(st.session_state.logs)))
        
        time.sleep(1)

    progress_bar.progress(1.0)
    status_text.success("すべての処理が完了しました！")
    st.balloons()
    
    # 完了処理
    st.session_state.storage = [] # 収納ボックスを空にする
    save_json(STORAGE_FILE, st.session_state.storage)
    
    time.sleep(3)
    st.session_state.is_running = False # フラグを戻す
    st.rerun() # トップ画面に戻る

# --- メイン画面 (通常時) ---
st.title("THREADS AUTO MASTER ♾️")

# サイドバー
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
    st.header("アカウント設定")
    with st.expander("➕ アカウント追加", expanded=True):
        c1, c2 = st.columns(2)
        nm = c1.text_input("名前", key="n_nm")
        uid = c2.text_input("User ID", key="n_id", type="password")
        sec = st.text_input("App Secret (任意)", key="n_sc", type="password")
        tok = st.text_input("Access Token", key="n_tk", type="password")
        if st.button("保存"):
            if nm and uid and tok:
                st.session_state.accounts.append({"name": nm, "id": uid, "token": tok, "secret": sec})
                save_json(ACCOUNTS_FILE, st.session_state.accounts)
                st.success(f"保存: {nm}")
    
    if st.session_state.accounts:
        st.markdown("### 連携中のアカウント")
        for i, acc in enumerate(st.session_state.accounts):
            c_inf, c_del = st.columns([4, 1])
            c_inf.write(f"✅ **{acc['name']}** (ID: {acc['id'][:4]}...)")
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
        
        # === 完了＆自動化ボタン ===
        if st.button("✅ 完了＆自動化スタート (即時実行)", type="primary"):
            current_post = st.session_state.posts[0]
            if not current_post['text'] and not current_post['image_file']:
                st.error("本文または画像を入力してください")
            else:
                target_acc_idx = current_post['acc_idx']
                
                # 1. 重複防止: 同じアカウントの古い待機投稿を削除
                st.session_state.storage = [p for p in st.session_state.storage if p['acc_idx'] != target_acc_idx]
                
                # 2. 新しい投稿を収納に追加
                st.session_state.storage.append(current_post)
                save_json(STORAGE_FILE, st.session_state.storage)
                
                # 3. 編集画面を即リセット
                st.session_state.posts = [{"text": "", "image_file": None, "acc_idx": 0, "random": False, "time_range": (12, 15)}]
                save_json(POSTS_FILE, st.session_state.posts)
                
                # 4. フラグを立ててリロード (画面切り替え)
                st.session_state.is_running = True
                st.rerun()

# --- ③ 実行ログ ---
with tab3:
    st.header("実行ログ履歴")
    if st.session_state.logs:
        st.code("\n".join(reversed(st.session_state.logs)))
    else:
        st.info("履歴はありません")
