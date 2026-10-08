"""Render only aggregate counts supplied by the authenticated React screen.

This service has no database access and receives no login tokens or user data.
"""
import streamlit as st
from streamlit_echarts import st_echarts

st.set_page_config(page_title="업무 현황", layout="wide", initial_sidebar_state="collapsed")
groups = [("in_progress", "진행 중", "#3478ff"), ("todo", "대기", "#ffac55"),
          ("done", "완료", "#0cbea0"), ("cancelled", "취소", "#c9cce0")]
data = []
for key, label, color in groups:
    try:
        count = int(st.query_params.get(key, "0"))
        if not 0 <= count <= 1_000_000:
            raise ValueError
    except ValueError:
        st.error("올바르지 않은 업무 수입니다.")
        st.stop()
    data.append({"name": label, "value": count, "itemStyle": {"color": color}})
total = sum(row["value"] for row in data)
st_echarts(options={
    "aria": {"enabled": True},
    "tooltip": {"trigger": "item", "formatter": "{b}: {c}개 ({d}%)"},
    "title": {"text": str(total), "subtext": "전체 업무", "left": "center", "top": "35%"},
    "legend": {"bottom": 0},
    "series": [{"type": "pie", "radius": ["55%", "75%"], "center": ["50%", "45%"],
                "label": {"show": False}, "data": data}],
}, height="250px", key="task-status")
if not total:
    st.caption("등록된 업무가 없습니다.")
