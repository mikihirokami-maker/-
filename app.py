import streamlit as st
import time
import random
import requests
import json
import os
import uuid # 追加：キーリセット用
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
        if 'image_files' in item_copy:
            del item_copy['image_files']
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
        p['image_files'] = [] 
        if 'next_run' in p and p['next_run']:
            try:
                p['next_run'] = datetime.fromisoformat(p['next_run'])
            except:
                p['next_run'] = None
    st.session_state.storage = loaded_st

if 'edit_target_idx' not in st.session_state: st.session_state.edit_target_idx = None
if 'logs' not in st.session_state: st.session_state.logs = []

# 【追加】フォームリセット用のキー管理
if 'form_key_suffix' not in st.session_state: st.session_state.form_key_suffix = str(uuid.uuid4())

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
    if target_time <= now:
        target_time = target_time + timedelta(days=1)
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

def post_to_threads(account, text, image_files=None):
    user_id = account['id']
    token = account['token']
    
    image_urls = []
    if image_files:
        for img_file in image_files:
            try:
                url = upload_image_to_imgur(img_file)
                if url: image_urls.append(url)
            except: pass
    
    base_url = f"https://graph.threads.net/v1.0/{user_id}/threads"
    
    try:
        if not image_urls:
            params = {'access_token': token, 'media_type': 'TEXT', 'text': text}
            res = requests.post(base_url, data=params).json()
            creation_id = res.get('id')
            
        elif len(image_urls) == 1:
            params = {
                'access_token': token, 
                'media_type': 'IMAGE', 
                'image_url': image_urls[0],
                'text': text
            }
            res = requests.post(base_url, data=params).json()
            creation_id = res.get('id')
            
        else:
            child_ids = []
            for img_url in image_urls:
                child_params = {
                    'access_token': token,
                    'media_type': 'IMAGE',
                    'image_url': img_url,
                    'is_carousel_item': 'true'
                }
                child_res = requests.post(base_url, data=child_params).json()
                if 'id' in child_res:
                    child_ids.append(child_res['id'])
                time.sleep(1) 
            
            if not child_ids: return False, "画像コンテナ作成失敗"
            
            carousel_params = {
                'access_token': token,
                'media_type': 'CAROUSEL',
                'children': ','.join(child_ids),
                'text': text
            }
            res = requests.post(base_url, data=carousel_params).json()
            creation_id = res.get('id')

        if not creation_id and 'error' in res:
            new_token = refresh_access_token(token)
            if new_token:
                account['token'] = new_token
                save_json(ACCOUNTS_FILE, st.session_state.accounts)
                return post_to_threads(account, text, image_files)
        
        if not creation_id: return False, f"投稿作成エラー: {res}"
        
        time.sleep(5) 
        url_publish = f"https://graph.threads.net/v1.0/{user_id}/threads_publish"
        pub_params = {'creation_id': creation_id, 'access_token': account['token']}
        pub_res = requests.post(url_publish, data=pub_params).json()
        
        return ('id' in pub_res, f"ID: {pub_res.get('id')}" if 'id' in pub_res else f"公開エラー: {pub_res}")
        
    except Exception as e:
        return False, str(e)

# --- メイン画面 ---
st.title("THREADS AUTO MASTER ♾️")

with st.sidebar:
    st.title("🤖 コントロールパネル")
    st.info(f"🇯🇵 {get_jst_time().strftime('%Y-%m-%d %H:%M:%S')}")
    is_running = st.toggle("🔄 モニタリング機能 (ON/OFF)", value=False)
    if is_running:
        st.caption("※モニタリング中も以下のスイッチで個別制御可能です")
    st.markdown("---")
    st.subheader("📡 アカウント別稼働設定")
    if st.session_state.accounts:
        for i, acc in enumerate(st.session_state.accounts):
            is_on = st.toggle(f"{acc['name']}", value=acc.get('active', True), key=f"side_acc_{i}")
            if is_on != acc.get('active', True):
                acc['active'] = is_on
                save_json(ACCOUNTS_FILE, st.session_state.accounts)
                st.rerun()
    else:
        st.caption("アカウントが登録されていません")
    st.markdown("---")
    if st.button("ログクリア"): st.session_state.logs = []
    st.markdown("### 📜 実行ログ")
    log_area = st.empty()
    if st.session_state.logs:
        log_area.code("\n".join(reversed(st.session_state.logs[-10:])))
    else:
        log_area.info("履歴なし")

tab1, tab2 = st.tabs(["① アカウント管理", "② 投稿ファクトリー"])

with tab1:
    st.header("アカウント設定")
    with st.expander("➕ アカウント追加", expanded=False):
        new_token = st.text_input("Access Token", type="password")
        new_secret = st.text_input("App Secret (任意)", type="password")
        if st.button("🔍 ID自動取得 & 保存"):
            if new_token:
                info = get_threads_user_info(new_token)
                if info:
                    st.session_state.accounts.append({
                        "name": f"{info.get('name')} (@{info.get('username')})", 
                        "id": info.get('id'), 
                        "token": new_token, 
                        "secret": new_secret,
                        "active": True
                    })
                    save_json(ACCOUNTS_FILE, st.session_state.accounts)
                    st.success(f"追加: {info.get('name')}")
                    st.rerun()
                else: st.error("取得失敗")
    st.markdown("---")
    if st.session_state.accounts:
        st.write("### 登録済みアカウント一覧")
        for i, acc in enumerate(st.session_state.accounts):
            with st.container():
                c1, c2 = st.columns([4, 1])
                status_text = "🟢 稼働中" if acc.get('active', True) else "⚪ 停止中"
                c1.write(f"**{acc['name']}** - {status_text}")
                if c2.button("削除", key=f"del_acc_{i}"):
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
                try:
                    original_idx = st.session_state.storage.index(p)
                    info_text = f"📝 {p['text'][:30]}..." if p['text'] else "📷 (画像のみ)"
                    if 'next_run' in p and p['next_run']:
                        info_text += f" | 🕒 次回: {p['next_run'].strftime('%m/%d %H:%M')}"
                    
                    if st.session_state.edit_target_idx == original_idx:
                        st.info(f"✏️ 編集中の項目: {info_text}")
                    else:
                        st.warning(info_text)
                    
                    if p.get('image_files'):
                        cols = st.columns(len(p['image_files']))
                        for idx, img in enumerate(p['image_files']):
                            with cols[idx]:
                                st.image(img, width=100, caption=f"画像{idx+1}")
                    
                    c_del, c_edit = st.columns([1, 1])
                    if c_del.button("🗑️ 削除", key=f"del_s_{original_idx}"):
                        st.session_state.storage.pop(original_idx)
                        if st.session_state.edit_target_idx == original_idx:
                            st.session_state.edit_target_idx = None
                        save_json(STORAGE_FILE, st.session_state.storage)
                        st.rerun()
                    if c_edit.button("✏️ 編集", key=f"edit_s_{original_idx}"):
                        st.session_state.edit_target_idx = original_idx
                        st.rerun()
                except ValueError:
                    continue

        st.markdown("---")
        form_title = "✏️ 投稿を編集" if st.session_state.edit_target_idx is not None else "📝 新しい自動投稿を追加"
        st.subheader(form_title)
        
        default_text = ""
        default_range = (12, 15)
        default_random = True
        
        # 編集モードの場合のみ値をセット
        if st.session_state.edit_target_idx is not None and st.session_state.edit_target_idx < len(st.session_state.storage):
            target_data = st.session_state.storage[st.session_state.edit_target_idx]
            default_text = target_data.get('text', "")
            default_range = target_data.get('time_range', (12, 15))
            default_random = target_data.get('random', True)

        # フォームリセット用のサフィックスをキーに追加
        suffix = st.session_state.form_key_suffix

        with st.container():
            chk_random = st.checkbox("⏰ ランダム時間を有効化", value=default_random, key=f"form_random_{suffix}")
            time_range = default_range
            if chk_random:
                time_range = st.slider("時間帯", 0, 24, default_range, key=f"form_slider_{suffix}")
                st.caption(f"※毎日 {time_range[0]}:00 〜 {time_range[1]}:00 の間で1回投稿します")
            
            c1, c2 = st.columns([1, 1])
            img_files = c1.file_uploader("画像 (複数選択可)", type=['png','jpg','jpeg','webp','heic'], accept_multiple_files=True, key=f"form_file_{suffix}")
            
            if img_files:
                c1.write(f"📸 {len(img_files)}枚 選択中")
                p_cols = c1.columns(min(len(img_files), 3))
                for i, img in enumerate(img_files[:3]):
                    p_cols[i].image(img, width=80)
                if len(img_files) > 3: c1.caption("...他")

            txt_content = c2.text_area("投稿本文", value=default_text, height=150, key=f"form_text_{suffix}")
            
            btn_label = "🔄 更新して保存" if st.session_state.edit_target_idx is not None else "✅ リストに追加 (毎日自動化)"
            
            if st.button(btn_label, type="primary"):
                if not txt_content and not img_files and (st.session_state.edit_target_idx is None or not st.session_state.storage[st.session_state.edit_target_idx].get('image_files')):
                    st.error("内容が空です")
                else:
                    new_next_run = calculate_next_run(time_range)
                    if st.session_state.edit_target_idx is not None:
                        idx = st.session_state.edit_target_idx
                        st.session_state.storage[idx]['text'] = txt_content
                        st.session_state.storage[idx]['random'] = chk_random
                        st.session_state.storage[idx]['time_range'] = time_range
                        st.session_state.storage[idx]['next_run'] = new_next_run
                        if img_files: 
                            st.session_state.storage[idx]['image_files'] = img_files
                        st.toast("設定を更新しました！")
                        st.session_state.edit_target_idx = None
                    else:
                        new_entry = {
                            "text": txt_content, 
                            "image_files": img_files,
                            "acc_idx": selected_acc_idx,
                            "random": chk_random, 
                            "time_range": time_range,
                            "next_run": new_next_run
                        }
                        st.session_state.storage.append(new_entry)
                        st.toast(f"{selected_acc_name} のリストに追加しました！")
                        
                        # 【重要】キーサフィックスを更新してフォームを強制リセット
                        st.session_state.form_key_suffix = str(uuid.uuid4())
                        
                    save_json(STORAGE_FILE, st.session_state.storage)
                    time.sleep(1)
                    st.rerun()
            
            if st.session_state.edit_target_idx is not None:
                if st.button("キャンセル"):
                    st.session_state.edit_target_idx = None
                    st.rerun()

if is_running:
    if st.session_state.edit_target_idx is not None:
         st.sidebar.warning("⚠️ 編集作業中は一時停止を推奨します")
    now = get_jst_time()
    run_triggered = False
    for p in st.session_state.storage:
        if p['acc_idx'] >= len(st.session_state.accounts): continue
        acc = st.session_state.accounts[p['acc_idx']]
        if not acc.get('active', True): continue
        
        if 'next_run' not in p or not isinstance(p['next_run'], datetime):
            p['next_run'] = calculate_next_run(p['time_range'])
            save_json(STORAGE_FILE, st.session_state.storage)
            
        time_diff = (p['next_run'] - now).total_seconds()
        
        if time_diff <= 0:
            suc, msg = post_to_threads(acc, p['text'], p.get('image_files'))
            now_s = now.strftime('%H:%M:%S')
            res_icon = "✅" if suc else "❌"
            log_entry = f"{res_icon} {now_s} [{acc['name']}] {msg}"
            st.session_state.logs.append(log_entry)
            
            p['next_run'] = schedule_for_tomorrow(p['time_range'])
            save_json(STORAGE_FILE, st.session_state.storage)
            st.toast(f"🚀 {acc['name']} に投稿しました！次回: {p['next_run'].strftime('%m/%d %H:%M')}")
            run_triggered = True
            
    time.sleep(10)
    if run_triggered:
        st.rerun()
    else:
        st.rerun()
