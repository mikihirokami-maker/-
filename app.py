import streamlit as st
import time
import random
import requests
from datetime import datetime, timedelta
import pandas as pd

# --- ページ設定 ---
st.set_page_config(page_title="Threads Auto Master", layout="wide", page_icon="🤖")

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
    .stTextInput, .stTextArea, .stSelectbox, .stTimeInput {
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
</style>
""", unsafe_allow_html=True)

# --- セッション状態の初期化 ---
if 'accounts' not in st.session_state:
    st.session_state.accounts = []  # アカウントリスト: [{'name': 'メイン', 'id': '...', 'token': '...'}]
if 'posts' not in st.session_state:
    st.session_state.posts = []     # 投稿リスト
if 'logs' not in st.session_state:
    st.session_state.logs = []      # 実行ログ

# --- API関数 ---
def post_to_threads(account, text, image_url=None):
    """Threads APIを使って投稿する"""
    user_id = account['id']
    token = account['token']
    
    # 1. コンテナ作成 (画像がある場合とない場合)
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
        # コンテナID取得
        res = requests.post(url_container, data=params).json()
        if 'id' not in res:
            return False, f"エラー(コンテナ作成): {res}"
        
        creation_id = res['id']
        
        # 2. 投稿公開 (Publish)
        url_publish = f"https://graph.threads.net/v1.0/{user_id}/threads_publish"
        pub_params = {
            'creation_id': creation_id,
            'access_token': token
        }
        pub_res = requests.post(url_publish, data=pub_params).json()
        
        if 'id' in pub_res:
            return True, f"投稿成功ID: {pub_res['id']}"
        else:
            return False, f"エラー(公開): {pub_res}"
            
    except Exception as e:
        return False, str(e)

# --- サイドバー: システム情報 ---
with st.sidebar:
    st.title("🤖 システム制御")
    st.success("システム稼働中")
    st.write(f"現在時刻: {datetime.now().strftime('%H:%M:%S')}")
    st.markdown("---")
    if st.button("ログをクリア"):
        st.session_state.logs = []

# --- メイン画面 ---
st.title("THREADS AUTO MASTER ⚡")

# タブ設定
tab_accounts, tab_posts, tab_run = st.tabs(["① アカウント設定", "② 投稿内容の作成", "③ 自動化実行モニター"])

# --- ① アカウント設定 ---
with tab_accounts:
    st.header("連携アカウント管理")
    st.info("ここで自動化したいアカウントを登録してください（複数可）")
    
    with st.expander("➕ 新しいアカウントを追加する", expanded=True):
        c1, c2 = st.columns(2)
        new_name = c1.text_input("アカウントの呼び名 (例: メイン垢)", key="new_acc_name")
        new_id = c2.text_input("Threads User ID", key="new_acc_id", type="password")
        new_token = st.text_input("Access Token", key="new_acc_token", type="password")
        
        if st.button("このアカウントを保存"):
            if new_name and new_id and new_token:
                st.session_state.accounts.append({
                    "name": new_name,
                    "id": new_id,
                    "token": new_token
                })
                st.success(f"アカウント「{new_name}」を保存しました！")
            else:
                st.error("全ての項目を入力してください")

    # 登録済みリスト表示
    st.markdown("### 登録済みアカウント一覧")
    if st.session_state.accounts:
        for idx, acc in enumerate(st.session_state.accounts):
            st.markdown(f"- **{acc['name']}** (ID: {acc['id'][:4]}****)")
    else:
        st.warning("まだアカウントが登録されていません")

# --- ② 投稿内容の作成 ---
with tab_posts:
    st.header("投稿スケジューラー")
    st.write("ここで投稿内容を作成します。枠はいくらでも増やせます。")
    
    if st.button("➕ 投稿枠を追加する"):
        st.session_state.posts.append({
            "text": "",
            "image": "",
            "account_idx": 0,
            "random_mode": False,
            "status": "待機中"
        })

    # 投稿カードの表示
    if not st.session_state.accounts:
        st.error("先に「① アカウント設定」でアカウントを登録してください。")
    else:
        for i, post in enumerate(st.session_state.posts):
            st.markdown(f"""<div class="post-card"><h4>投稿 #{i+1}</h4>""", unsafe_allow_html=True)
            
            col_a, col_b = st.columns([1, 2])
            
            with col_a:
                # アカウント選択
                acc_names = [a['name'] for a in st.session_state.accounts]
                selected_acc = st.selectbox(f"投稿するアカウント (#{i+1})", acc_names, key=f"acc_select_{i}")
                # ランダム設定
                is_random = st.checkbox("⏰ ランダム時間に投稿 (0:00-24:00)", key=f"rnd_{i}")
                if is_random:
                    st.caption("※今日の中のどこかの時間で自動投稿されます")
                else:
                    st.caption("※実行ボタンを押すと即時投稿されます")
            
            with col_b:
                text_content = st.text_area(f"投稿本文 (#{i+1})", placeholder="ここに投稿内容を入力...", key=f"text_{i}")
                image_url = st.text_input(f"画像URL (任意) (#{i+1})", placeholder="https://... (画像がある場合のみ)", key=f"img_{i}")
            
            # データ更新
            st.session_state.posts[i]["text"] = text_content
            st.session_state.posts[i]["image"] = image_url
            st.session_state.posts[i]["account_idx"] = acc_names.index(selected_acc)
            st.session_state.posts[i]["random_mode"] = is_random
            
            if st.button(f"🗑️ 削除 (#{i+1})", key=f"del_{i}"):
                st.session_state.posts.pop(i)
                st.rerun()
            
            st.markdown("</div>", unsafe_allow_html=True)

# --- ③ 自動化実行モニター ---
with tab_run:
    st.header("自動化コントロールセンター")
    
    st.markdown("""
    実行ボタンを押すと、設定されたスケジュールに従って処理を開始します。
    **※ブラウザのこのタブを開いたままにしてください。**
    """)
    
    if st.button("🚀 自動化プロセスを開始 (START)", type="primary"):
        st.toast("自動化を開始しました！ログを確認してください。", icon="🤖")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 投稿処理ループ
        for i, post in enumerate(st.session_state.posts):
            account = st.session_state.accounts[post['account_idx']]
            text = post['text']
            img = post['image']
            is_random = post['random_mode']
            
            if not text and not img:
                continue
            
            status_text.text(f"処理中: 投稿 #{i+1} ({account['name']})...")
            
            # ランダムモードの場合の待機ロジック (デモ用に短縮していますが、本来は長時間待機)
            if is_random:
                wait_sec = random.randint(1, 10) # テスト用に数秒にしています。本番は sleep時間を大きくする
                st.info(f"投稿 #{i+1} はランダム設定です。{wait_sec}秒後に投稿します...")
                time.sleep(wait_sec)
            
            # 投稿実行
            success, msg = post_to_threads(account, text, img)
            
            # ログ記録
            timestamp = datetime.now().strftime('%H:%M:%S')
            if success:
                st.session_state.logs.append(f"✅ [{timestamp}] 成功: {account['name']} - {text[:10]}...")
                st.balloons()
            else:
                st.session_state.logs.append(f"❌ [{timestamp}] 失敗: {account['name']} - {msg}")
            
            progress_bar.progress((i + 1) / len(st.session_state.posts))
            time.sleep(1)
        
        status_text.text("全プロセスの処理が完了しました。")

    # ログ表示エリア
    st.markdown("### 📜 実行ログ")
    log_area = st.container()
    with log_area:
        for log in reversed(st.session_state.logs):
            st.code(log)
