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
        width: 100%;
    }
    .post-card { background: rgba(255, 255, 255, 0.05); padding: 20px; border-radius: 15px; border: 1px solid #00f2ff; margin-bottom: 20px; }
    .status-card { background: rgba(0, 0, 0, 0.5); padding: 10px; border-radius: 8px; border-left: 4px solid #00f2ff; margin-bottom: 5px; }
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
        target_time = now + timedelta(seconds=10) # 過ぎていれば即時(テスト用)
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

# ==========================================
# 🖥️ メイン画面構成
# ==========================================
st.title("THREADS AUTO MASTER ♾️")

# --- サイドバー ---
with st.sidebar:
    st.title("🤖 設定")
    st.info(f"🇯🇵 {get_jst_time().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if st.button("ログをクリア"): st.session_state.logs = []
    
    with st.expander("アカウント追加"):
        new_token = st.text_input("New Token", type="password")
        if st.button("ID自動追加"):
            if new_token:
                info = get_threads_user_info(new_token)
                if info:
                    st.session_state.accounts.append({
                        "name": f"{info.get('name')} (@{info.get('username')})", 
                        "id": info.get('id'), "token": new_token
                    })
                    save_json(ACCOUNTS_FILE, st.session_state.accounts)
                    st.success("追加完了")
                    time.sleep(1) # 少し待ってリロード
                    st.rerun()

# --- 上段: 新規投稿作成エリア (常に表示) ---
st.subheader("📝 新規投稿の作成 & スケジュール")

if not st.session_state.accounts:
    st.warning("左のサイドバーからアカウントを追加してください")
else:
    # アカウント選択
    acc_names = [a['name'] for a in st.session_state.accounts]
    selected_acc_name = st.selectbox("アカウントを選択", acc_names)
    selected_acc_idx = acc_names.index(selected_acc_name)
    
    # 既存設定の確認
    current = next((p for p in st.session_state.storage if p['acc_idx'] == selected_acc_idx), None)
    
    with st.container():
        st.markdown(f"""<div class="post-card">""", unsafe_allow_html=True)
        
        # フォーム
        chk_random = st.checkbox("⏰ 時間帯ランダム投稿", value=True, key=f"r_main")
        time_range = (12, 15)
        if chk_random:
            time_range = st.slider("時間帯を指定", 0, 24, (9, 21), key=f"sl_main")
            st.caption(f"※{time_range[0]}:00 〜 {time_range[1]}:00 の間で毎日1回投稿します")
        
        c1, c2 = st.columns([1, 1])
        img_file = c1.file_uploader("画像 (任意)", type=['png','jpg'], key=f"f_main")
        if img_file: c1.image(img_file, width=150)
        
        txt_content = c2.text_area("投稿本文", height=150, key=f"t_main")
        
        # 保存ボタン (これを押すとリロードされ、下の監視ループが再開する)
        if st.button("✅ この内容で自動化をスケジュールする (上書き)", type="primary"):
            if not txt_content and not img_file:
                st.error("内容が空です")
            else:
                # 既存を削除 (1垢1枠)
                st.session_state.storage = [p for p in st.session_state.storage if p['acc_idx'] != selected_acc_idx]
                
                # 新規追加
                new_entry = {
                    "text": txt_content,
                    "image_file": img_file,
                    "acc_idx": selected_acc_idx,
                    "random": chk_random,
                    "time_range": time_range,
                    "next_run": calculate_next_run(time_range)
                }
                st.session_state.storage.append(new_entry)
                save_json(STORAGE_FILE, st.session_state.storage)
                
                st.toast(f"{selected_acc_name} の設定を保存しました！自動化を開始します...")
                time.sleep(1)
                st.rerun() # リロードして監視ループへ
        
        st.markdown("</div>", unsafe_allow_html=True)

    if current:
        st.info(f"ℹ️ 現在の予定: {current['next_run'].strftime('%m/%d %H:%M')} (内容は保持されています)")
        if st.button("🗑️ 現在の設定を削除"):
            st.session_state.storage.remove(current)
            save_json(STORAGE_FILE, st.session_state.storage)
            st.rerun()

st.markdown("---")

# --- 下段: 監視モニター (自動実行ループ) ---
st.subheader("🤖 稼働中のオートメーション")
st.caption("※この画面を開いている間、設定された時間に自動投稿されます。")

monitor_placeholder = st.empty()
log_placeholder = st.empty()

# ★ここが心臓部: 常にループして監視する★
# ユーザーが「保存」ボタンなどを押すと、Streamlitはこのループを中断してスクリプトを再実行するため、
# 「止める」操作は不要になります。
while True:
    now = get_jst_time()
    
    # 表示用HTML生成
    status_html = ""
    if not st.session_state.storage:
        status_html = "<p style='color: grey;'>現在稼働中のスケジュールはありません。</p>"
    
    for i, p in enumerate(st.session_state.storage):
        if p['acc_idx'] >= len(st.session_state.accounts): continue
        acc = st.session_state.accounts[p['acc_idx']]
        
        # スケジュール補正
        if 'next_run' not in p or not isinstance(p['next_run'], datetime):
            p['next_run'] = calculate_next_run(p['time_range'])
            save_json(STORAGE_FILE, st.session_state.storage)
        
        time_diff = (p['next_run'] - now).total_seconds()
        
        # 投稿判定
        if time_diff <= 0:
            # 実行！
            monitor_placeholder.warning(f"🚀 {acc['name']} 投稿開始...")
            suc, res_msg = post_to_threads(acc, p['text'], p['image_file'])
            
            # ログ保存
            now_s = now.strftime('%H:%M:%S')
            icon = "✅" if suc else "❌"
            st.session_state.logs.append(f"{icon} {now_s} [{acc['name']}] {res_msg}")
            
            # 次回スケジュール (明日)
            p['next_run'] = schedule_for_tomorrow(p['time_range'])
            save_json(STORAGE_FILE, st.session_state.storage)
            
            st.toast(f"{acc['name']} 投稿完了！次回は明日です。")
            time.sleep(2)
            st.rerun() # 完了後はリロードして表示更新
            
        else:
            # 待機中表示
            nxt = p['next_run'].strftime('%m/%d %H:%M:%S')
            
            # 60秒以内で黄色くする演出
            color = "#00f2ff" if time_diff > 60 else "yellow"
            msg = f"次回: {nxt}" if time_diff > 60 else f"⚡ まもなく投稿: あと {int(time_diff)}秒"
            
            status_html += f"""
            <div class="status-card" style="border-left-color: {color};">
                <div style="font-weight:bold; color:white;">{acc['name']}</div>
                <div style="color: {color};">{msg}</div>
                <div style="font-size:0.8em; color:#aaa;">設定範囲: {p['time_range'][0]}:00 - {p['time_range'][1]}:00</div>
            </div>
            """

    # 画面更新
    monitor_placeholder.markdown(status_html, unsafe_allow_html=True)
    
    if st.session_state.logs:
        log_placeholder.code("\n".join(reversed(st.session_state.logs)))
    
    time.sleep(1) # 1秒待機してループ
