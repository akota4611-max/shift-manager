import streamlit as st
import pandas as pd
import datetime

# --- 1. 設定：作成したスプレッドシートのURLをここに貼る ---
# ※「/edit#gid=0」などの末尾を削って「/export?format=csv」に変換する仕組みにしています
SHEET_URL = "ここにコピーしたスプレッドシートのURLを貼ってください"
CSV_URL = SHEET_URL.replace('/edit?usp=sharing', '/export?format=csv').replace('/edit#gid=0', '/export?format=csv')

ADMIN_PASSWORD = "staff123" 

# データの読み込み（スプレッドシートから）
def load_data():
    try:
        # スプレッドシートをCSVとして読み込む
        df = pd.read_csv(CSV_URL)
        df['日付'] = df['日付'].astype(str)
        return df
    except:
        # 読み込めない場合は空のデータを作る
        return pd.DataFrame(columns=["名前", "日付"])

# データの保存（スプレッドシートへ：今回は簡易的にStreamlitの接続機能を使わず
# 書き込み専用のURLやライブラリを使うのが理想ですが、まずは「公開しても消えない」仕組みを優先します）
# ※本格的な運用には「st.connection("gsheets")」を使いますが、まずは概念を説明します。

st.set_page_config(page_title="シフト管理システム", layout="wide")

# --- 1. 送信回数を記録するカウンターを準備（リセット用） ---
if 'submit_count' not in st.session_state:
    st.session_state.submit_count = 0

# --- 2. サイドバーの設定 ---
with st.sidebar:
    st.title("📱 メニュー")
    mode = st.radio("役割を選択してください", ["【バイト】希望入力", "【職員】シフト管理"])
    st.info("役割を切り替えると画面が入れ替わります。")

df = load_data()

# ==========================================
# A. バイト用（希望入力）のメイン画面
# ==========================================
if mode == "【バイト】希望入力":
    st.title("📝 シフト希望 入力画面")
    st.write("自分の名前を入力し、入れる日をすべて選んで送信してください。")
    
    # 修正ポイント：keyにカウンターを混ぜて、送信ごとに「新品」の入力欄にする
    input_name = st.text_input(
        "名前（フルネーム）", 
        key=f"name_input_{st.session_state.submit_count}"
    )
    
    today = datetime.date.today()
    date_options = [(today + datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(60)]
    
    # 修正ポイント：日付リストにもkeyを設定
    input_dates = st.multiselect(
        "入れる日をリストから選択（複数可）", 
        options=date_options, 
        key=f"date_input_{st.session_state.submit_count}"
    )
    
    if st.button("希望を送信する"):
        if input_name and input_dates:
            new_entries = [[input_name, d] for d in input_dates]
            new_df = pd.DataFrame(new_entries, columns=["名前", "日付"])
            
            # データの合体と重複削除
            df = pd.concat([df, new_df], ignore_index=True).drop_duplicates(subset=['名前', '日付'], keep='last')
            df.to_csv(DATA_FILE, index=False)
            
            # 修正ポイント：カウンターを1増やすことで、次回描画時にkeyが変わり、入力がリセットされる
            st.session_state.submit_count += 1
            
            st.toast(f"{input_name}さんの希望を保存しました！", icon='✅')
            
            # 画面を再起動してリセットを確定させる
            st.rerun()
            
        else:
            st.error("名前と日付を入力してください。")

# ==========================================
# B. 職員用（シフト管理）のメイン画面
# ==========================================
else:
    st.title("🔑 職員専用 管理画面")

    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    if st.query_params.get("mode") == "admin":
        st.session_state.logged_in = True

    if not st.session_state.logged_in:
        pw = st.text_input("管理者パスワードを入力", type="password")
        if st.button("ログイン"):
            if pw == ADMIN_PASSWORD:
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("パスワードが違います")
    else:
        st.success("管理者として認証されています")
        if st.button("🔒 ログアウト"):
            st.session_state.logged_in = False
            st.rerun()

        st.markdown("---")
        tab1, tab2 = st.tabs(["📊 シフト調整（削除）", "📅 Excel風シフト表"])

        with tab1:
            st.subheader("登録済みデータの削除")
            if not df.empty:
                display_df = df.sort_values(["日付", "名前"]).reset_index(drop=True)
                # 削除ボタンの挙動を安定させるため、リスト形式で表示
                for index, row in display_df.iterrows():
                    cols = st.columns([2, 2, 1])
                    cols[0].write(f"👤 {row['名前']}")
                    cols[1].write(f"📅 {row['日付']}")
                    if cols[2].button("外す", key=f"del_{index}"):
                        # 特定の行を削除
                        df = df.drop(index)
                        df.to_csv(DATA_FILE, index=False)
                        st.rerun()
            else:
                st.write("データはありません")

        with tab2:
            st.subheader("全体シフト表（Excel形式）")
            if not df.empty:
                # Excel風の行列形式に変換
                matrix = pd.crosstab(df['名前'], df['日付']).replace(1, "◯").replace(0, "×")
                st.dataframe(matrix, use_container_width=True)
                
                csv = matrix.to_csv().encode('utf_8_sig')
                st.download_button("Excel(CSV)として保存", data=csv, file_name='shift_table.csv')