import streamlit as st
import csv
import io
import json
import os
from datetime import datetime
from collections import defaultdict

# Optional: supabase client for remote persistence
_HAS_SUPABASE = False
try:
    from supabase import create_client
    _HAS_SUPABASE = True
except Exception:
    # supabase not installed or import failed; fall back to local file storage
    _HAS_SUPABASE = False

# 设置页面配置
st.set_page_config(
    page_title="房产记账工具",
    page_icon="🏠",
    layout="wide"
)

# 创建数据目录
DATA_DIR = "user_data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)


# --- Remote persistence helpers (Supabase) ---
def _has_remote_config():
    # Streamlit secrets can store SUPABASE_URL and SUPABASE_KEY
    try:
        return bool(st.secrets.get("SUPABASE_URL") and st.secrets.get("SUPABASE_KEY") and _HAS_SUPABASE)
    except Exception:
        return False


def _get_supabase_client():
    """Return a Supabase client using Streamlit secrets. Caller should check _has_remote_config() first."""
    url = st.secrets.get("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY")
    return create_client(url, key)


def load_user_data_remote(username: str):
    """Load user data from a Supabase table named `ledgers` with columns (username text primary key, data jsonb).
    Returns None if not found.
    """
    try:
        client = _get_supabase_client()
        resp = client.table("ledgers").select("data").eq("username", username).execute()
        data_rows = resp.data if hasattr(resp, "data") else resp.get("data")
        if data_rows:
            return data_rows[0].get("data") if isinstance(data_rows[0], dict) else None
    except Exception as e:
        # don't crash the app for remote errors; fall back to local
        st.error(f"远程加载数据失败: {e}")
    return None


def save_user_data_remote(username: str, data: dict):
    """Upsert user data into Supabase `ledgers` table."""
    try:
        client = _get_supabase_client()
        # upsert with primary key = username
        client.table("ledgers").upsert({"username": username, "data": data}).execute()
        return True
    except Exception as e:
        st.error(f"远程保存数据失败: {e}")
        return False

# --- end remote helpers ---

# 加载用户数据
def load_user_data():
    """Load user data for current session. If remote (Supabase) is configured, prefer remote data.

    Falls back to local JSON file in `user_data/` if remote isn't available or lookup fails.
    """
    username = st.session_state.username
    if not username:
        st.session_state.properties = {"默认房产": []}
        return

    # Try remote first if configured
    if _has_remote_config():
        remote = load_user_data_remote(username)
        if remote is not None:
            st.session_state.properties = remote.get("properties", {}) if isinstance(remote, dict) else {"默认房产": []}
            if not st.session_state.properties:
                st.session_state.properties = {"默认房产": []}
            return

    # Fallback to local file
    user_file = os.path.join(DATA_DIR, f"{username}.json")
    if os.path.exists(user_file):
        with open(user_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            st.session_state.properties = data.get("properties", {})
            # 确保有一个默认房产
            if not st.session_state.properties:
                st.session_state.properties = {"默认房产": []}
    else:
        st.session_state.properties = {"默认房产": []}

# 保存用户数据
def save_user_data():
    """Save current user's data. If remote is configured, try remote upsert and fall back to local file on failure."""
    username = st.session_state.username
    if not username:
        return

    data = {
        "username": username,
        "properties": st.session_state.properties
    }

    # If remote storage available, try that first
    if _has_remote_config():
        ok = save_user_data_remote(username, data)
        if ok:
            return

    # Fallback to local file storage
    try:
        user_file = os.path.join(DATA_DIR, f"{username}.json")
        with open(user_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"本地保存数据失败: {e}")

# 应用标题
st.title("🏠 房产记账工具")
st.markdown("---")

# 用户登录/注册
if 'username' not in st.session_state:
    st.session_state.username = None
    st.session_state.properties = {}
    st.session_state.current_property = "默认房产"

if st.session_state.username is None:
    st.subheader("用户登录")
    
    with st.form("login_form"):
        username = st.text_input("用户名")
        login_button = st.form_submit_button("登录")
        
        if login_button and username:
            st.session_state.username = username
            # 初始化用户数据
            load_user_data()
            # 设置当前房产为第一个房产
            if st.session_state.properties:
                st.session_state.current_property = list(st.session_state.properties.keys())[0]
            st.rerun()
else:
    st.sidebar.write(f"欢迎, {st.session_state.username}!")
    if st.sidebar.button("退出登录"):
        st.session_state.username = None
        st.session_state.properties = {}
        st.session_state.current_property = "默认房产"
        st.rerun()

# 定义预设费用类型
PRESET_EXPENSE_TYPES = ["契税", "土地出让金", "中介费", "装修费"]

# 主要应用逻辑
if st.session_state.username:
    # 房产选择和管理
    st.sidebar.subheader("房产管理")
    
    # 选择当前房产
    property_names = list(st.session_state.properties.keys())
    if property_names:
        st.session_state.current_property = st.sidebar.selectbox(
            "选择房产", 
            property_names, 
            index=property_names.index(st.session_state.current_property) if st.session_state.current_property in property_names else 0
        )
    else:
        st.session_state.current_property = "默认房产"
        st.session_state.properties[st.session_state.current_property] = []
    
    # 添加新房产
    with st.sidebar.form("add_property_form"):
        new_property_name = st.text_input("新房产名称")
        add_property_button = st.form_submit_button("添加房产")
        
        if add_property_button and new_property_name:
            if new_property_name not in st.session_state.properties:
                st.session_state.properties[new_property_name] = []
                save_user_data()
                st.success(f"已添加房产: {new_property_name}")
                st.rerun()
            else:
                st.warning("房产名称已存在")
    
    # 删除当前房产
    if len(st.session_state.properties) > 1:
        if st.sidebar.button(f"删除房产 '{st.session_state.current_property}'"):
            del st.session_state.properties[st.session_state.current_property]
            # 设置当前房产为第一个房产
            st.session_state.current_property = list(st.session_state.properties.keys())[0]
            save_user_data()
            st.rerun()
    
    # 获取当前房产的费用记录
    current_expenses = st.session_state.properties.get(st.session_state.current_property, [])
    
    # 侧边栏输入表单
    with st.sidebar:
        st.header(f"添加费用记录 - {st.session_state.current_property}")
        
        # 费用类型选择（独立于表单）。不使用 on_change 回调以避免在表单上下文中触发 StreamlitAPIException。
        st.selectbox(
            "费用类型",
            PRESET_EXPENSE_TYPES + ["其他"],
            key="expense_type",
            help="选择费用类型，选择‘其他’可自定义名称"
        )

        # 如果选择"其他"，显示自定义费用名称文本框（也在表单外部以便即时显示）
        if st.session_state.get("expense_type") == "其他":
            st.text_input("自定义费用名称", key="custom_type")

        # 表单（只包含不需要回调的控件）
        with st.form(key="expense_form"):
            date = st.date_input("日期", value=datetime.now().date())
            amount = st.number_input("金额", min_value=0.0, step=100.0, format="%.2f")
            description = st.text_area("描述（可选）")

            submit_button = st.form_submit_button(label="添加记录")

            if submit_button:
                if amount > 0:
                    # 在提交时决定最终的费用类型（优先自定义值）
                    chosen_type = st.session_state.get("expense_type")
                    if chosen_type == "其他":
                        custom = st.session_state.get("custom_type", "")
                        if custom:
                            chosen_type = custom

                    expense_record = {
                        "日期": date.strftime("%Y-%m-%d"),
                        "费用类型": chosen_type,
                        "金额": amount,
                        "描述": description
                    }
                    # 确保当前房产存在
                    if st.session_state.current_property not in st.session_state.properties:
                        st.session_state.properties[st.session_state.current_property] = []
                    st.session_state.properties[st.session_state.current_property].append(expense_record)
                    save_user_data()  # 保存数据
                    st.success(f"已添加 {chosen_type} 记录！")
                else:
                    st.error("金额必须大于0")

    # 主内容区域
    col1, col2 = st.columns([3, 1])

    with col1:
        st.subheader(f"费用明细 - {st.session_state.current_property}")
        
        if current_expenses:
            # 显示费用记录表格
            # 创建表头
            header_cols = st.columns([2, 2, 2, 3, 1])
            header_cols[0].write("**日期**")
            header_cols[1].write("**费用类型**")
            header_cols[2].write("**金额**")
            header_cols[3].write("**描述**")
            header_cols[4].write("**操作**")
            
            # 显示每条记录
            for i, expense in enumerate(current_expenses):
                # 使用container来更好地组织每行记录
                with st.container():
                    record_cols = st.columns([2, 2, 2, 3, 1])
                    record_cols[0].write(expense["日期"])
                    record_cols[1].write(expense["费用类型"])
                    record_cols[2].write(f"¥{expense['金额']:,.2f}")
                    record_cols[3].write(expense["描述"] if expense["描述"] else "-")
                    
                    # 添加删除按钮
                    if record_cols[4].button("🗑️", key=f"delete_{i}"):
                        # 删除指定索引的费用记录
                        st.session_state.properties[st.session_state.current_property].pop(i)
                        save_user_data()  # 保存数据
                        st.rerun()
            
            # 提供下载功能
            def convert_to_csv():
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(["日期", "费用类型", "金额", "描述"])
                for expense in current_expenses:
                    writer.writerow([
                        expense["日期"],
                        expense["费用类型"],
                        expense["金额"],
                        expense["描述"]
                    ])
                return output.getvalue().encode('utf-8')
            
            st.download_button(
                label="📥 下载CSV文件",
                data=convert_to_csv(),
                file_name=f'房产费用明细_{st.session_state.current_property}_{datetime.now().strftime("%Y%m%d")}.csv',
                mime='text/csv'
            )
        else:
            st.info("暂无费用记录，请在左侧添加记录。")

    with col2:
        st.subheader("统计信息")
        
        if current_expenses:
            # 计算总费用
            total_amount = sum(expense["金额"] for expense in current_expenses)
            st.metric("总费用", f"¥{total_amount:,.2f}")
            
            # 按费用类型分组统计
            st.write("**按类型统计:**")
            type_summary = defaultdict(float)
            for expense in current_expenses:
                type_summary[expense["费用类型"]] += expense["金额"]
            
            # 转换为排序后的列表
            sorted_summary = sorted(type_summary.items(), key=lambda x: x[1], reverse=True)
            
            for expense_type, amount in sorted_summary:
                st.write(f"{expense_type}: ¥{amount:,.2f}")
                
            # 简单文本形式的费用分布
            st.write("**费用分布:**")
            for expense_type, amount in sorted_summary:
                percentage = (amount / total_amount) * 100 if total_amount > 0 else 0
                st.progress(percentage / 100)
                st.write(f"{expense_type}: {percentage:.1f}%")
        else:
            st.info("暂无统计数据")

    # 清空当前房产的所有记录按钮
    if current_expenses:
        if st.button("🗑️ 清空当前房产的所有记录"):
            st.session_state.properties[st.session_state.current_property] = []
            save_user_data()  # 保存数据
            st.rerun()
else:
    st.info("请输入用户名登录以使用应用。")