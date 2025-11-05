import streamlit as st
import csv
import io
from datetime import datetime
from collections import defaultdict

# 设置页面配置
st.set_page_config(
    page_title="房产记账工具",
    page_icon="🏠",
    layout="wide"
)

# 应用标题
st.title("🏠 房产记账工具")
st.markdown("---")

# 初始化session state
if 'expenses' not in st.session_state:
    st.session_state.expenses = []

# 定义预设费用类型
PRESET_EXPENSE_TYPES = ["契税", "土地出让金", "中介费", "装修费"]

# 侧边栏输入表单
with st.sidebar:
    st.header("添加费用记录")
    
    # 表单
    with st.form(key="expense_form"):
        date = st.date_input("日期", value=datetime.now().date())
        expense_type = st.selectbox("费用类型", PRESET_EXPENSE_TYPES + ["其他"])
        
        # 如果选择"其他"，允许用户自定义费用名称
        if expense_type == "其他":
            custom_type = st.text_input("自定义费用名称")
            expense_type = custom_type if custom_type else "其他"
            
        amount = st.number_input("金额", min_value=0.0, step=100.0, format="%.2f")
        description = st.text_area("描述（可选）")
        
        submit_button = st.form_submit_button(label="添加记录")
        
        if submit_button:
            if amount > 0:
                expense_record = {
                    "日期": date.strftime("%Y-%m-%d"),
                    "费用类型": expense_type,
                    "金额": amount,
                    "描述": description
                }
                st.session_state.expenses.append(expense_record)
                st.success(f"已添加 {expense_type} 记录！")
            else:
                st.error("金额必须大于0")

# 主内容区域
col1, col2 = st.columns([3, 1])

with col1:
    st.subheader("费用明细")
    
    if st.session_state.expenses:
        # 显示费用记录表格
        # 创建表头
        cols = st.columns([2, 2, 2, 3])
        cols[0].write("**日期**")
        cols[1].write("**费用类型**")
        cols[2].write("**金额**")
        cols[3].write("**描述**")
        
        # 显示每条记录
        for expense in st.session_state.expenses:
            cols = st.columns([2, 2, 2, 3])
            cols[0].write(expense["日期"])
            cols[1].write(expense["费用类型"])
            cols[2].write(f"¥{expense['金额']:,.2f}")
            cols[3].write(expense["描述"] if expense["描述"] else "-")
        
        # 提供下载功能
        def convert_to_csv():
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["日期", "费用类型", "金额", "描述"])
            for expense in st.session_state.expenses:
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
            file_name=f'房产费用明细_{datetime.now().strftime("%Y%m%d")}.csv',
            mime='text/csv'
        )
    else:
        st.info("暂无费用记录，请在左侧添加记录。")

with col2:
    st.subheader("统计信息")
    
    if st.session_state.expenses:
        # 计算总费用
        total_amount = sum(expense["金额"] for expense in st.session_state.expenses)
        st.metric("总费用", f"¥{total_amount:,.2f}")
        
        # 按费用类型分组统计
        st.write("**按类型统计:**")
        type_summary = defaultdict(float)
        for expense in st.session_state.expenses:
            type_summary[expense["费用类型"]] += expense["金额"]
        
        # 转换为排序后的列表
        sorted_summary = sorted(type_summary.items(), key=lambda x: x[1], reverse=True)
        
        for expense_type, amount in sorted_summary:
            st.write(f"{expense_type}: ¥{amount:,.2f}")
            
        # 简单文本形式的费用分布
        st.write("**费用分布:**")
        for expense_type, amount in sorted_summary:
            percentage = (amount / total_amount) * 100
            st.progress(percentage / 100)
            st.write(f"{expense_type}: {percentage:.1f}%")
    else:
        st.info("暂无统计数据")

# 清空所有记录按钮
if st.session_state.expenses:
    if st.button("🗑️ 清空所有记录"):
        st.session_state.expenses = []
        st.rerun()