import streamlit as st
import time
import random
import requests
import json
import os
import uuid
from datetime import datetime, timedelta, timezone

# --- ページ設定 ---
st.set_page_config(page_title="Threads Auto Master Pro", layout="wide", page_icon="🤖")

# --- デザイン設定 ---
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #e0e0e0; }
    h1, h2, h3 { color: #00f2ff !important; font-family: 'Helvetica Neue', sans-serif; }
    .stButton>button {
        background: linear-gradient(90deg, #00c6ff, #0072ff); color: white; font-weight: bold; border: none; border-radius: 8px;
    }
    .task-card {
        background-color: #1e2130; padding: 15px; border-radius: 10px; border-left: 5px solid #00f2ff; margin-bottom: 10px;
    }
    .status-box {
        padding: 10px; border-radius: 5px; background-color: #262730; border: 1px solid #444; margin-bottom: 5px;
    }
</style>
""", unsafe_allow_html=True)

# --- 定数・パス ---
ACCOUNTS_FILE = "accounts.json"
STORAGE_FILE = "storage.json"
IMAGE_DIR = "uploaded_images"

if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

# --- データ保存・読み込み関数 ---
def load_json(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_json(file_path, data):
    # datetimeオブジェクトなどを文字列に変換して保存
    serializable_data = []
    for item in data:
        item_copy = item.copy()
        if 'next_run' in item_copy and isinstance(item_copy['next_run'], datetime):
            item_copy['next_run'] = item_copy['next_run'].isoformat()
        serializable_data.append(item_copy)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(serializable_data, f, ensure_ascii=False, indent=2)

def save_uploaded_image(uploaded_file):
    """アップロードされた画像をローカルに保存し、パスを返す"""
    if uploaded_file is None:
        return None
    file_path = os.path.join(IMAGE_DIR, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path

# --- セッション初期化 ---
if 'accounts' not in st.session_state: st.session_state.accounts = load_json(ACCOUNTS_FILE)
if 'storage' not in st.session_state:
    loaded_st = load_json(STORAGE_FILE)
    # 文字列の日時をdatetimeオブジェクトに復元
    for p in loaded_st: 
        if 'next_run' in p and p['next_run']:
            try:
                p['next_run'] = datetime.fromisoformat(p['next_run'])
            except:
                p['next_run'] = None
        if 'id' not in p: p['id'] = str(uuid.uuid4()) # IDがない場合は付与
    st.session_state.storage = loaded_st

if 'logs' not in st.session_state: st.session_state.logs = []
# ボットの稼働状態はサイドバーのチェックボックスで管理するためsession_stateでのフラグ管理は最小限に

# --- ユーティリティ ---
def get_jst_time():
    JST = timezone(timedelta(hours=9))
    return datetime.now(JST)

def calculate_next_run(time_range):
    """
    指定された時間帯(start, end)の中でランダムな時間を決定する。
    もしその時間が「今日すでに過ぎている」場合は、「明日のその時間」にする。
    """
    s, e = time_range
    if s >= e: e = 24 # 範囲がおかしい場合の補正
    
    now = get_jst_time()
    
    # 今日のターゲット時間を生成
    target_h = random.randint(s, max(s, e-1))
    target_m = random.randint(0, 59)
    target_time = now.replace(hour=target_h, minute=target_m, second=0, microsecond=0)
    
    # 生成した時間が現在より過去なら、明日に設定する
    if target_time <= now:
        target_time = target_time + timedelta(days=1)
        
    return target_time

# --- API関連 ---
def refresh_access_token(token):
    url = "https://graph.threads.net/refresh_access_token"
    params = {'grant_type': 'th_refresh_token', 'access_token': token}
    try:
        res = requests.get(url, params=params).json()
        return res.get('access_token')
    except: return None

def upload_image_to_imgur(image_path):
    CLIENT_ID = "d3a6697416345f7" 
    url = "https://api.imgur.com/3/image"
    headers = {"Authorization": f"Client-ID {CLIENT_ID}"}
    try:
        with open(image_path, "rb") as img:
            payload = {"image": img.read()}
            response = requests.post(url, headers=headers, files=payload)
            data = response.json()
            return data['data']['link'] if data['success'] else None
    except Exception as e:
        return None

def post_to_threads(account, text, image_path=None):
    user_id = account['id']
    token = account['token']
    image_url = None
    
    if image_path and os.path.exists(image_path):
        image_url = upload_image_to_imgur(image_path)
        if not image_url:
            return False, "画像のアップロードに失敗しました"
    
    url_container = f"https://graph.threads.net/v1.0/{user_id}/threads"
    params = {'access_token': token, 'media_type': 'IMAGE' if image_url else 'TEXT'}
    if image_url: params['image_url'] = image_url
    params['text'] = text

    try:
        res = requests.post(url_container, data=params).json()
        
        # トークン切れ対応
        if 'error' in res or 'id' not in res:
            new_token = refresh_access_token(token)
            if new_token:
                account['token'] = new_token
                save_json(ACCOUNTS_FILE, st.session_state.accounts)
                params['access_token'] = new_token
                res = requests.post(url_container, data=params).json()
        
        if 'id' not in res: return False, f"APIエラー: {res}"
        
        creation_id = res['id']
        time.sleep(10 if image_url else 2) # 画像処理待ち
        
        url_publish = f"https://graph.threads.net/v1.0/{user_id}/threads_publish"
        pub_params = {'creation_id': creation_id, 'access_token': account['token']}
        pub_res = requests.post(url_publish, data=pub_params).json()
        
        return ('id' in pub_res, f"公開成功 ID: {pub_res.get('id')}" if 'id' in pub_res else f"公開失敗: {pub_res}")
    except Exception as e:
        return False, str(e)

# --- サイドバー (設定 & 起動スイッチ) ---
with st.sidebar:
    st.title("🤖 制御パネル")
    st.write(f"現在時刻: {get_jst_time().strftime('%H:%M:%S')}")
    
    # アカウント管理
    with st.expander("👤 アカウント設定", expanded=False):
        new_token = st.text_input("Access Token", type="password")
        if st.button("アカウント追加"):
            if new_token:
                url = "https://graph.threads.net/v1.0/me"
                res = requests.get(url, params={'fields': 'id,username,name', 'access_token': new_token}).json()
                if 'id' in res:
                    st.session_state.accounts.append({
                        "name": res.get('username'), "id": res.get('id'), "token": new_token
                    })
                    save_json(ACCOUNTS_FILE, st.session_state.accounts)
                    st.success("追加しました")
                    st.rerun()
                else:
                    st.error("トークンが無効です")
        
        if st.session_state.accounts:
            st.divider()
            for i, acc in enumerate(st.session_state.accounts):
                c1, c2 = st.columns([3, 1])
                c1.write(f"@{acc['name']}")
                if c2.button("削除", key=f"del_acc_{i}"):
                    st.session_state.accounts.pop(i)
                    save_json(ACCOUNTS_FILE, st.session_state.accounts)
                    st.rerun()

    st.divider()
    
    # ★★★ ここが新しい起動スイッチ ★★★
    st.header("稼働スイッチ")
    run_bot = st.toggle("自動投稿を開始する", value=False)
    
    if run_bot:
        st.warning("⚠️ スイッチONの間は、この画面を開いたままにしてください。自動投稿ループが実行されます。")
        st.info("設定を変更する場合はスイッチをOFFにしてください。")

# --- メイン画面 ---

if not run_bot:
    # === 編集モード (スイッチOFF時) ===
    st.title("📝 投稿タスクの編集")
    
    if not st.session_state.accounts:
        st.error("まずはサイドバーからアカウントを追加してください。")
    else:
        # アカウント選択
        acc_names = [a['name'] for a in st.session_state.accounts]
        selected_acc_name = st.selectbox("アカウント選択", acc_names)
        selected_acc_idx = acc_names.index(selected_acc_name)

        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("新規タスク追加")
            with st.form("add_task_form"):
                txt_content = st.text_area("投稿内容", height=150)
                img_file = st.file_uploader("画像 (任意)", type=['png', 'jpg', 'jpeg'])
                
                # 時間設定
                time_range = st.slider("投稿する時間帯 (時)", 0, 24, (9, 21))
                st.caption(f"※毎日 {time_range[0]}:00 〜 {time_range[1]}:00 の間のどこかでランダムに投稿されます。")
                
                submitted = st.form_submit_button("➕ このタスクをスケジュールに追加")
                
                if submitted:
                    if not txt_content and not img_file:
                        st.error("テキストか画像を入力してください")
                    else:
                        # 画像保存
                        saved_img_path = save_uploaded_image(img_file)
                        
                        # 次回実行時間の計算 (ロジック修正済み)
                        next_run_time = calculate_next_run(time_range)
                        
                        new_entry = {
                            "id": str(uuid.uuid4()),
                            "acc_idx": selected_acc_idx,
                            "text": txt_content,
                            "image_path": saved_img_path, # パスで保存
                            "time_range": time_range,
                            "next_run": next_run_time
                        }
                        
                        st.session_state.storage.append(new_entry)
                        save_json(STORAGE_FILE, st.session_state.storage)
                        st.success(f"追加しました！ 次回投稿予定: {next_run_time.strftime('%m/%d %H:%M')}")
                        time.sleep(1)
                        st.rerun()

        with col2:
            st.subheader(f"@{selected_acc_name} の待機中タスク")
            
            # このアカウントのタスクを抽出
            my_tasks = [t for t in st.session_state.storage if t['acc_idx'] == selected_acc_idx]
            
            if not my_tasks:
                st.info("現在スケジュールされているタスクはありません。")
            
            for task in my_tasks:
                with st.container():
                    st.markdown(f"""
                    <div class="task-card">
                        <b>予定時刻:</b> {task['next_run'].strftime('%m/%d %H:%M')}<br>
                        <b>内容:</b> {task['text'][:30]}...
                    </div>
                    """, unsafe_allow_html=True)
                    
                    c_del, c_view = st.columns([1, 4])
                    if c_del.button("削除", key=f"del_{task['id']}"):
                        st.session_state.storage = [t for t in st.session_state.storage if t['id'] != task['id']]
                        save_json(STORAGE_FILE, st.session_state.storage)
                        st.rerun()

else:
    # === 実行モード (スイッチON時) ===
    st.title("🚀 自動投稿システム稼働中")
    st.markdown("設定を変更するにはサイドバーのスイッチをOFFにしてください。")
    
    log_placeholder = st.empty()
    status_placeholder = st.empty()
    
    # 実行ループ
    while run_bot:
        now = get_jst_time()
        executed_flag = False
        
        # ステータス表示の更新
        status_html = "<h4>📅 スケジュール状況</h4>"
        sorted_tasks = sorted(st.session_state.storage, key=lambda x: x['next_run'])
        
        for task in sorted_tasks:
            if task['acc_idx'] < len(st.session_state.accounts):
                acc_name = st.session_state.accounts[task['acc_idx']]['name']
                t_str = task['next_run'].strftime('%m/%d %H:%M:%S')
                # カウントダウン計算
                diff = (task['next_run'] - now).total_seconds()
                color = "#00ff00" if diff < 3600 else "#e0e0e0"
                status_html += f"<div class='status-box' style='border-color:{color}'><b>@{acc_name}</b> | 予定: {t_str}</div>"
        
        status_placeholder.markdown(status_html, unsafe_allow_html=True)

        # 投稿チェック処理
        for i, task in enumerate(st.session_state.storage):
            # アカウントインデックスが有効か確認
            if task['acc_idx'] >= len(st.session_state.accounts): continue
            
            # 時間チェック
            if task['next_run'] <= now:
                acc = st.session_state.accounts[task['acc_idx']]
                
                # 投稿実行
                with st.spinner(f"@{acc['name']} に投稿中..."):
                    suc, msg = post_to_threads(acc, task['text'], task.get('image_path'))
                
                # ログ記録
                res_icon = "✅" if suc else "❌"
                log_entry = f"{res_icon} {now.strftime('%H:%M')} [@{acc['name']}] {msg}"
                st.session_state.logs.insert(0, log_entry)
                
                # 次回の予約計算
                # 今回の時間に基づいてではなく、「明日」のランダムな時間にする
                # まずタスクのnext_runを明日の日付にシフトしてからランダム時間を適用するアプローチ
                next_day_range = calculate_next_run(task['time_range'])
                
                # もし計算結果が現在より過去なら(論理的にありえないが念の為)、さらに1日足す
                if next_day_range <= now:
                     next_day_range += timedelta(days=1)

                task['next_run'] = next_day_range
                save_json(STORAGE_FILE, st.session_state.storage)
                
                executed_flag = True
        
        # ログ表示更新
        log_txt = "\n".join(st.session_state.logs[:10])
        log_placeholder.code(log_txt if log_txt else "まだ実行履歴はありません...")
        
        if executed_flag:
            st.toast("タスクを実行しました！")
            time.sleep(2) # 連続投稿防止とUI更新待ち
            st.rerun() # 画面リフレッシュ
            
        time.sleep(1) # CPU負荷軽減のための待機
