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
    .bot-status { border: 1px solid #00f2ff; padding: 15px; border-radius: 10px; margin-bottom: 10px; background-color: #050505; }
    img { border-radius: 10px; border: 1px solid #333; margin-top: 10px; }
</style>
""", unsafe_allow_html=True)

# --- データ保存・読み込み ---
ACCOUNTS_FILE = "accounts.json"
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
        if 'next_run' in item_copy and isinstance(item_copy['next_run'], datetime):
            item_copy['next_run'] = item_copy['next_run'].isoformat()
        serializable_data.append(item_copy)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(serializable_data, f, ensure_ascii=False, indent=2)

# --- セッション初期化 ---
if 'accounts' not in st.session_state: st.session_state.accounts = load_json(ACCOUNTS_FILE)
if 'storage' not in st.session_state:
    loaded_st = load_json(STORAGE_FILE)
    for p in loaded_st: 
        p['image_file'] = None
        if 'next_run' in p and p['next_run']:
            try:
                p['next_run'] = datetime.fromisoformat(p['next_run'])
            except:
                p['next_run'] = None
    st.session_state.storage = loaded_st

if 'logs' not in st.session_state: st.session_state.logs = []
if 'is_bot_running' not in st.session_state: st.session_state.is_bot_running = False

# --- ユーティリティ ---
def get_jst_time():
    JST = timezone(timedelta(hours=9))
    return datetime.now(JST)

def calculate_next_run(time_range):
    s, e = time_range
    if s >= e: e = 24
    now = get_jst_time()
    
    target_h = random.randint(s, max(s, e-1))
    target_m = random.randint(0, 59)
    target_time = now.replace(hour=target_h, minute=target_m, second=0)
    
    if target_time < now:
        target_time = now + timedelta(seconds=10)
        
    return target_time

def schedule_for_tomorrow(time_range):
    s, e = time_range
    if s >= e: e = 24
    now = get_jst_time()
    tomorrow = now + timedelta(days=1)
    
    target_h = random.randint(s, max(s, e-1))
    target_m = random.randint(0, 59)
    target_time = tomorrow.replace(hour=target_h, minute=target_m, second=0)
    return target_time

# --- API関連 ---
def get_threads_user_info(token):
    url = "https://graph.threads.net/v1.0/me"
    params = {'fields': 'id,username,name', 'access_token': token}
    try:
        res = requests.get(url, params=params).json()
        return res if 'id' in res else None
    except: return None

def refresh_access_token(token):
    url = "https://graph.threads.net/refresh_access_token"
    params = {'grant_type': 'th_refresh_token', 'access_token': token}
    try:
        res = requests.get(url, params=params).json()
        return res.get('access_token')
    except: return None

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
    except: return None

def post_to_threads(account, text, image_obj=None):
    user_id = account['id']
    token = account['token']
    image_url = None
    
    if image_obj is not None:
        try:
            image_url = upload_image_to_imgur(image_obj)
        except:
            return False, "画像の再アップロードに失敗(セッション切れ)"
    
    url_container = f"https://graph.threads.net/v1.0/{user_id}/threads"
    params = {'access_token': token, 'media_type': 'IMAGE' if image_url else 'TEXT'}
    if image_url: params['image_url'] = image_url
    params['text'] = text

    try:
        res = requests.post(url_container, data=params).json()
        if 'error' in res or 'id' not in res:
            new_token = refresh_access_token(token)
            if new_token:
                account['token'] = new_token
                save_json(ACCOUNTS_FILE, st.session_state.accounts)
                params['access_token'] = new_token
                res = requests.post(url_container, data=params).json()
        
        if 'id' not in res: return False, f"エラー: {res}"
        
        creation_id = res['id']
        if image_url: time.sleep(10)
        else: time.sleep(2)
        
        url_publish = f"https://graph.threads.net/v1.0/{user_id}/threads_publish"
        pub_params = {'creation_id': creation_id, 'access_token': account['token']}
        pub_res = requests.post(url_publish, data=pub_params).json()
        
        return ('id' in pub_res, f"ID: {pub_res.get('id')}" if 'id' in pub_res else f"公開エラー: {pub_res}")
    except Exception as e:
        return False, str(e)

# --- ボット実行画面 ---
if st.session_state.is_bot_running:
    st.title("🤖 自動投稿ボット稼働中")
    
    c1, c2 = st.columns([1, 4])
    with c1:
        if st.button("⛔ ボットを停止して戻る"):
            st.session_state.is_bot_running = False
            st.rerun()
    with c2:
        st.info("この画面を開いたままにしてください。毎日指定時間に投稿されます。")

    status_area = st.empty()
    log_area = st.empty()
    
    while st.session_state.is_bot_running:
        now = get_jst_time()
        active_tasks = 0
        
        for i, p in enumerate(st.session_state.storage):
            if p['acc_idx'] >= len(st.session_state.accounts): continue
            acc = st.session_state.accounts[p['acc_idx']]
            
            if 'next_run' not in p or not isinstance(p['next_run'], datetime):
                p['next_run'] = calculate_next_run(p['time_range'])
                save_json(STORAGE_FILE, st.session_state.storage)
            
            time_diff = (p['next_run'] - now).total_seconds()
            
            if time_diff <= 0:
                status_area.warning(f"🚀 {acc['name']} の投稿を実行中...")
                suc, msg = post_to_threads(acc, p['text'], p['image_file'])
                
                now_s = now.strftime('%H:%M:%S')
                res_icon = "✅" if suc else "❌"
                log_entry = f"{res_icon} {now_s} [{acc['name']}] {msg}"
                st.session_state.logs.append(log_entry)
                
                p['next_run'] = schedule_for_tomorrow(p['time_range'])
                save_json(STORAGE_FILE, st.session_state.storage)
                
                status_area.success(f"完了！次回は {p['next_run'].strftime('%m/%d %H:%M')} です")
                time.sleep(5)
            else:
                active_tasks += 1
        
        status_html = "### 📅 現在のスケジュール状況<br>"
        for p in st.session_state.storage:
            if p['acc_idx'] < len(st.session_state.accounts):
                aname = st.session_state.accounts[p['acc_idx']]['name']
                nxt = p['next_run'].strftime('%m/%d %H:%M:%S')
                status_html += f"<div class='bot-status'><b>{aname}</b><br>次回投稿: {nxt}</div>"
        
        status_area.markdown(status_html, unsafe_allow_html=True)
        log_area.code("\n".join(reversed(st.session_state.logs)))
        
        time.sleep(1)

# --- メイン画面 ---
st.title("THREADS AUTO MASTER ♾️")

with st.sidebar:
    st.title("🤖 システム制御")
    st.info(f"🇯🇵 {get_jst_time().strftime('%Y-%m-%d %H:%M:%S')}")
    if st.button("ログクリア"): st.session_state.logs = []

tab1, tab2, tab3 = st.tabs(["① アカウント設定", "② 投稿作成 (アカウント別)", "③ ボット起動"])

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
                else: st.error("取得失敗")
    
    if st.session_state.accounts:
        for i, acc in enumerate(st.session_state.accounts):
            c1, c2 = st.columns([4, 1])
            c1.write(f"✅ **{acc['name']}**")
            if c2.button("削除", key=f"d{i}"):
                st.session_state.accounts.pop(i)
                save_json(ACCOUNTS_FILE, st.session_state.accounts)
                st.rerun()

with tab2:
    st.header("投稿ファクトリー")
    
    if not st.session_state.accounts:
        st.warning("まずはアカウントを追加してください")
    else:
        acc_names = [a['name'] for a in st.session_state.accounts]
        selected_acc_name = st.selectbox("⚡ 作業するアカウントを選択", acc_names)
        selected_acc_idx = acc_names.index(selected_acc_name)
        
        st.markdown("---")
        
        st.subheader(f"📦 {selected_acc_name} の自動投稿リスト")
        my_storage = [p for p in st.session_state.storage if p['acc_idx'] == selected_acc_idx]
        
        if not my_storage:
            st.info("このアカウントには自動投稿が設定されていません。")
        else:
            for p in my_storage:
                original_idx = st.session_state.storage.index(p)
                info_text = f"内容: {p['text'][:20]}... "
                if 'next_run' in p and p['next_run']:
                    info_text += f" | 🕒 次回: {p['next_run'].strftime('%H:%M')}"
                st.warning(info_text)
                if st.button("🗑️ 設定を削除", key=f"del_s_{original_idx}"):
                    st.session_state.storage.pop(original_idx)
                    save_json(STORAGE_FILE, st.session_state.storage)
                    st.rerun()

        st.markdown("---")
        
        st.subheader("📝 新しい自動投稿を設定")
        with st.container():
            chk_random = st.checkbox("⏰ ランダム時間を有効化", value=True, key=f"r_{selected_acc_idx}")
            time_range = (12, 15)
            if chk_random:
                time_range = st.slider("時間帯", 0, 24, (9, 21), key=f"sl_{selected_acc_idx}")
                # ここを修正：変数の値を埋め込んで表示
                st.caption(f"※毎日 {time_range[0]}:00 〜 {time_range[1]}:00 の間で1回投稿します")
            
            c1, c2 = st.columns([1, 1])
            img_file = c1.file_uploader("画像 (任意)", type=['png','jpg'], key=f"f_{selected_acc_idx}")
            if img_file: c1.image(img_file, width=150)
            
            txt_content = c2.text_area("投稿本文", height=150, key=f"t_{selected_acc_idx}")
            
            if st.button("✅ 設定を保存 (毎日自動化)", type="primary", key=f"btn_{selected_acc_idx}"):
                if not txt_content and not img_file:
                    st.error("内容が空です")
                else:
                    st.session_state.storage = [p for p in st.session_state.storage if p['acc_idx'] != selected_acc_idx]
                    new_entry = {
                        "text": txt_content, "image_file": img_file, "acc_idx": selected_acc_idx,
                        "random": chk_random, "time_range": time_range,
                        "next_run": calculate_next_run(time_range)
                    }
                    st.session_state.storage.append(new_entry)
                    save_json(STORAGE_FILE, st.session_state.storage)
                    st.toast(f"{selected_acc_name} のスケジュールを保存しました！")
                    time.sleep(1)
                    st.rerun()

with tab3:
    st.header("🚀 自動投稿ボット")
    st.write("全ての設定が終わったら、ここでボットを起動してください。")
    st.info(f"現在、{len(st.session_state.storage)} 件のアカウントがスケジュールされています。")
    if st.button("🚀 ボットを起動する (開始)", type="primary"):
        st.session_state.is_bot_running = True
        st.rerun()
