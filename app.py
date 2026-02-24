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
# モード管理: 'running' (稼働中) または 'editing' (作成中)
if 'app_mode' not in st.session_state: st.session_state.app_mode = 'running' 

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
        if image_url: time.sleep(10) # 待機
        else: time.sleep(2)
        
        url_publish = f"https://graph.threads.net/v1.0/{user_id}/threads_publish"
        pub_params = {'creation_id': creation_id, 'access_token': account['token']}
        pub_res = requests.post(url_publish, data=pub_params).json()
        
        return ('id' in pub_res, f"ID: {pub_res.get('id')}" if 'id' in pub_res else f"公開エラー: {pub_res}")
    except Exception as e:
        return False, str(e)

# --- アプリのメイン構造 ---
st.title("THREADS AUTO MASTER ♾️")

# サイドバー（共通）
with st.sidebar:
    st.title("🤖 システム制御")
    st.info(f"🇯🇵 {get_jst_time().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # モード切替スイッチ（ボタン）
    if st.session_state.app_mode == 'running':
        if st.button("✏️ 止めて新規作成する"):
            st.session_state.app_mode = 'editing'
            st.rerun()
    else:
        if st.button("↩️ 作成をやめて稼働に戻る"):
            st.session_state.app_mode = 'running'
            st.rerun()

    st.markdown("---")
    if st.button("ログクリア"): st.session_state.logs = []
    
    # アカウント管理 (簡易)
    with st.expander("アカウント設定"):
        new_token = st.text_input("New Access Token", type="password")
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
                    st.rerun()

# ==========================================
# 🅰️ 稼働モード (Running Mode) - デフォルト
# ==========================================
if st.session_state.app_mode == 'running':
    st.header("🤖 自動投稿ボット稼働中")
    st.caption("この画面を開いたままにしてください。設定された時間帯に毎日自動投稿します。")
    
    status_area = st.empty()
    log_area = st.empty()
    
    # 無限ループで監視
    while True:
        # モードが切り替わったらループを抜ける
        if st.session_state.app_mode != 'running':
            st.rerun()
            
        now = get_jst_time()
        
        # 保存されている全タスクをチェック
        status_html = "### 📅 現在のスケジュール状況<br>"
        
        if not st.session_state.storage:
            status_html += "<p>まだ自動投稿が設定されていません。「✏️ 新規作成」から追加してください。</p>"
        
        for i, p in enumerate(st.session_state.storage):
            if p['acc_idx'] >= len(st.session_state.accounts): continue
            acc = st.session_state.accounts[p['acc_idx']]
            
            # スケジュール修復
            if 'next_run' not in p or not isinstance(p['next_run'], datetime):
                p['next_run'] = calculate_next_run(p['time_range'])
                save_json(STORAGE_FILE, st.session_state.storage)
            
            time_diff = (p['next_run'] - now).total_seconds()
            
            # ステータス表示作成
            nxt_str = p['next_run'].strftime('%m/%d %H:%M:%S')
            style = "border-color: #00f2ff;"
            msg = f"次回投稿: {nxt_str}"
            
            if time_diff <= 0:
                # 実行タイム！
                status_area.warning(f"🚀 {acc['name']} の投稿を実行中...")
                suc, res_msg = post_to_threads(acc, p['text'], p['image_file'])
                
                now_s = now.strftime('%H:%M:%S')
                icon = "✅" if suc else "❌"
                st.session_state.logs.append(f"{icon} {now_s} [{acc['name']}] {res_msg}")
                
                # 次回 (明日) のスケジュールへ更新
                p['next_run'] = schedule_for_tomorrow(p['time_range'])
                save_json(STORAGE_FILE, st.session_state.storage)
                
                status_area.success(f"完了！次回は {p['next_run'].strftime('%m/%d %H:%M')} です")
                time.sleep(3)
                st.rerun() # 画面更新
                
            elif time_diff < 60:
                style = "border-color: yellow; color: yellow;"
                msg = f"⚡ まもなく投稿 ({int(time_diff)}秒後)..."
            
            status_html += f"<div class='bot-status' style='{style}'><b>{acc['name']}</b><br>{msg}</div>"
        
        status_area.markdown(status_html, unsafe_allow_html=True)
        
        # ログ表示
        if st.session_state.logs:
            log_area.code("\n".join(reversed(st.session_state.logs)))
        
        time.sleep(1) # 1秒ごとにチェック

# ==========================================
# 🅱️ 編集モード (Editing Mode)
# ==========================================
elif st.session_state.app_mode == 'editing':
    st.header("📝 新規投稿の作成")
    
    if not st.session_state.accounts:
        st.warning("左のサイドバーからアカウントを追加してください")
    else:
        # アカウント選択
        acc_names = [a['name'] for a in st.session_state.accounts]
        selected_acc_name = st.selectbox("アカウントを選択", acc_names)
        selected_acc_idx = acc_names.index(selected_acc_name)
        
        st.markdown("---")
        
        # 既存設定の確認
        current_setting = next((p for p in st.session_state.storage if p['acc_idx'] == selected_acc_idx), None)
        if current_setting:
            st.info(f"💡 このアカウントには既に設定があります (次回: {current_setting['next_run'].strftime('%H:%M')})。保存すると上書きされます。")
            if st.button("🗑️ 設定を削除して停止する"):
                st.session_state.storage.remove(current_setting)
                save_json(STORAGE_FILE, st.session_state.storage)
                st.success("削除しました")
                st.rerun()
        
        # 作成フォーム
        with st.container():
            chk_random = st.checkbox("⏰ ランダム時間を有効化", value=True)
            time_range = (12, 15)
            if chk_random:
                time_range = st.slider("時間帯", 0, 24, (9, 21))
                # ユーザー要望: 自分で決めた時間であることを明示
                st.caption(f"※毎日 {time_range[0]}:00 〜 {time_range[1]}:00 の間でランダムに1回投稿します")
            
            c1, c2 = st.columns([1, 1])
            img_file = c1.file_uploader("画像 (任意)", type=['png','jpg'])
            if img_file: c1.image(img_file, width=150)
            
            txt_content = c2.text_area("投稿本文", height=150)
            
            if st.button("✅ 保存して自動化を再開 (Running)", type="primary"):
                if not txt_content and not img_file:
                    st.error("内容が空です")
                else:
                    # 古い設定を削除 (1垢1枠)
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
                    
                    st.toast(f"{selected_acc_name} の設定を保存しました！稼働モードに戻ります...")
                    time.sleep(1)
                    
                    # モードを戻してリラン
                    st.session_state.app_mode = 'running'
                    st.rerun()
