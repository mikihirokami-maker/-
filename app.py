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

# --- データの保存・読み込み機能 (アカウント消失防止) ---
DATA_FILE = "accounts.json"

def load_accounts_from_file():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_accounts_to_file(accounts):
    with open(DATA_FILE, 'w') as f:
        json.dump(accounts, f)

# --- セッション状態の初期化 ---
if 'accounts' not in st.session_state:
    st.session_state.accounts = load_accounts_from_file() # ファイルから読み込み

if 'posts' not in st.session_state:
    # 最初は「1つ」だけ空の枠を用意する
    st.session_state.posts = [{"text": "", "image_file": None, "acc_idx": 0, "random": False, "time_range": (12, 15)}]

if 'storage' not in st.session_state: st.session_state.storage = []
if 'logs' not in st.session_state: st.session_state.logs = []

# --- 日本時間(JST)の取得関数 ---
def get_jst_time():
    JST = timezone(timedelta(hours=9))
    return datetime.now(JST)

# --- API関数 ---
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
                # トークン更新があったのでファイルも更新して保存
                save_accounts_to_file(st.session_state.accounts)
                
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

# --- サイドバー ---
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
            save_accounts_to_file(st.session_state.accounts) # 更新後のトークンを保存
            st.success(f"{c}件更新完了＆保存しました")
        else:
            st.warning("更新対象なし")
            
    if st.button("ログクリア"): st.session_state.logs = []

# --- メイン画面 ---
st.title("THREADS AUTO MASTER ♾️")

tab1, tab2, tab3 = st.tabs(["① アカウント設定", "② 投稿作成＆収納", "③ 自動化実行"])

# --- ① アカウント ---
with tab1:
    st.header("アカウント設定")
    st.info("※ここで入力したアカウントは自動保存され、更新ボタンを押しても消えません。")
    
    with st.expander("➕ アカウント追加", expanded=True):
        c1, c2 = st.columns(2)
        nm = c1.text_input("名前", key="n_nm")
        uid = c2.text_input("User ID", key="n_id", type="password")
        sec = st.text_input("App Secret (任意)", key="n_sc", type="password")
        tok = st.text_input("Access Token", key="n_tk", type="password")
        
        if st.button("保存"):
            if nm and uid and tok:
                st.session_state.accounts.append({"name": nm, "id": uid, "token": tok, "secret": sec})
                save_accounts_to_file(st.session_state.accounts) # ファイルに書き込み
                st.success(f"保存しました: {nm}")
            else:
                st.error("必須項目を入力してください")
    
    if st.session_state.accounts:
        st.markdown("### 連携中のアカウント")
        for i, acc in enumerate(st.session_state.accounts):
            c_info, c_del = st.columns([4, 1])
            c_info.write(f"✅ **{acc['name']}** (ID: {acc['id'][:4]}...)")
            if c_del.button("削除", key=f"del_acc_{i}"):
                st.session_state.accounts.pop(i)
                save_accounts_to_file(st.session_state.accounts) # 削除後も保存
                st.rerun()

# --- ② 投稿作成＆収納 ---
with tab2:
    st.header("投稿ファクトリー")
    
    # --- 収納ボックスエリア ---
    with st.expander("📦 収納ボックス (作成済み投稿)を見る"):
        if not st.session_state.storage:
            st.info("現在、収納されている投稿はありません。")
        else:
            for i, stored_post in enumerate(st.session_state.storage):
                st.markdown(f"""<div class="storage-box"><b>📦 収納データ #{i+1}</b><br>内容: {stored_post['text'][:20]}...</div>""", unsafe_allow_html=True)
                if st.button(f"↩️ 取り出す (編集画面へ戻す) #{i+1}", key=f"restore_{i}"):
                    st.session_state.posts.append(stored_post)
                    st.session_state.storage.pop(i)
                    st.rerun()

    st.markdown("---")
    st.subheader("作業デスク (編集中の投稿)")
    
    if st.button("➕ 新規投稿枠を追加"):
        st.session_state.posts.append({"text": "", "image_file": None, "acc_idx": 0, "random": False, "time_range": (12, 15)})
    
    if not st.session_state.accounts:
        st.warning("先にアカウントを追加してください")
    else:
        acc_names = [a['name'] for a in st.session_state.accounts]
        
        # 編集中の投稿を表示
        for i, post in enumerate(st.session_state.posts):
            st.markdown(f"""<div class="post-card"><h4>📝 編集中の投稿 #{i+1}</h4>""", unsafe_allow_html=True)
            c1, c2 = st.columns([1, 1])
            with c1:
                # アカウント選択 (インデックスエラー防止)
                if post['acc_idx'] >= len(acc_names): post['acc_idx'] = 0
                post['acc_idx'] = acc_names.index(st.selectbox(f"アカウント #{i+1}", acc_names, index=post['acc_idx'], key=f"s_{i}"))
            with c2:
                post['random'] = st.checkbox(f"ランダム時間 #{i+1}", value=post['random'], key=f"r_{i}")
                if post['random']:
                    s, e = st.slider(f"時間帯 #{i+1}", 0, 24, post['time_range'], key=f"sl_{i}")
                    post['time_range'] = (s, e)
            
            c3, c4 = st.columns([1, 1])
            with c3:
                up = st.file_uploader(f"画像 #{i+1}", type=['png','jpg'], key=f"f_{i}")
                if up: 
                    post['image_file'] = up
                    st.image(up, width=150)
            with c4:
                post['text'] = st.text_area(f"本文 #{i+1}", value=post['text'], height=100, key=f"t_{i}")
            
            if st.button(f"🗑️ 削除 #{i+1}", key=f"d_{i}"):
                st.session_state.posts.pop(i)
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        # --- 完了ボタンエリア ---
        if st.session_state.posts:
            st.markdown("---")
            if st.button("✅ 投稿作成完了 (収納ボックスへしまう)", type="primary"):
                # 現在の編集内容をすべてstorageに移動
                st.session_state.storage.extend(st.session_state.posts)
                # 投稿枠を完全に空にするのではなく、新しい1つの枠を用意する（ユーザビリティのため）
                st.session_state.posts = [{"text": "", "image_file": None, "acc_idx": 0, "random": False, "time_range": (12, 15)}]
                st.balloons()
                st.success("全ての投稿を収納ボックスにしまいました！新しい枠を用意しました。")
                time.sleep(1)
                st.rerun()

# --- ③ 自動化実行 ---
with tab3:
    st.header("自動化実行")
    st.write("収納ボックスに入っている投稿、または編集中の投稿すべてをスケジュール実行します。")
    
    # 実行対象を結合 (編集中のもの + 収納されているもの)
    all_targets = [p for p in st.session_state.posts if p['text'] or p['image_file']] + st.session_state.storage
    st.info(f"現在の待機中ポスト: {len(all_targets)}件")
    
    if st.button("🚀 自動化スタート"):
        if not all_targets:
            st.error("投稿データがありません。")
        else:
            st.toast("開始します...")
            log = st.empty()
            
            for i, post in enumerate(all_targets):
                acc = st.session_state.accounts[post['acc_idx']]
                
                if post['random']:
                    s, e = post['time_range']
                    if s >= e: e = 24
                    now = get_jst_time() 
                    
                    target_h = random.randint(s, max(s, e-1))
                    target_m = random.randint(0, 59)
                    target_time = now.replace(hour=target_h, minute=target_m, second=0)
                    
                    wait = (target_time - now).total_seconds()
                    
                    if wait > 0:
                        st.info(f"待機中... {target_h}:{target_m} に投稿します ({int(wait)}秒後)")
                        time.sleep(wait)
                    else:
                        st.warning(f"設定時間({target_h}:{target_m})を過ぎているため即時投稿します")
                        time.sleep(3)
                
                suc, msg = post_to_threads(acc, post['text'], post['image_file'])
                now_s = get_jst_time().strftime('%H:%M:%S')
                res_icon = "✅" if suc else "❌"
                st.session_state.logs.append(f"{res_icon} {now_s} [{acc['name']}] {msg}")
                
                log.code("\n".join(reversed(st.session_state.logs)))
            
            st.success("全処理完了")
