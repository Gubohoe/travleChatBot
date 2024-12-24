import streamlit as st
import pandas as pd
import json

# JSON 파일 읽기
def load_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

# JSON 파일 저장
def save_json(data, file_path):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 문자열을 개별 일정으로 분리
def split_schedule(schedule_str):
    if not schedule_str:
        return []
    return [s.strip() for s in schedule_str.split(',')]

# 개별 일정을 다시 문자열로 결합
def join_schedule(schedule_list):
    return ', '.join(schedule_list)

# 초기 데이터 로드
if 'travel_plan' not in st.session_state:
    try:
        st.session_state.travel_plan = load_json("result.json")
    except FileNotFoundError:
        st.error("result.json 파일을 찾을 수 없습니다. 파일을 확인해주세요.", icon="🚨")

if __name__ == "__main__":
    st.title("📝 여행 일정 관리")

    # CSS 스타일링은 이전과 동일하게 유지...
    st.markdown("""
        <style>
            body {
                font-family: 'Comic Sans MS', cursive, sans-serif;
                background-color: #f0f8ff;
                color: #333;
                margin: 0;
                padding: 0;
            }
            .header {
                background-color: #ff6347;
                color: white;
                padding: 25px;
                text-align: center;
                font-size: 36px;
                font-weight: bold;
                border-radius: 15px;
                box-shadow: 0px 8px 15px rgba(0, 0, 0, 0.2);
                margin-bottom: 30px;
            }
            .subheader {
                font-size: 24px;
                font-weight: bold;
                color: #e74c3c;
            }
            .section {
                background-color: #ffffff;
                padding: 20px;
                border-radius: 15px;
                box-shadow: 0px 6px 12px rgba(0, 0, 0, 0.1);
                margin: 15px;
                max-width: 1000px;
                margin-left: auto;
                margin-right: auto;
            }
            .dataframe-container {
                padding: 0;
                margin: 0;
            }
            .stDataFrame {
                border: none;
            }
            .schedule-item {
                padding: 10px;
                margin: 5px 0;
                border-radius: 5px;
                background-color: #f8f9fa;
                border-left: 4px solid #e74c3c;
            }
        </style>
    """, unsafe_allow_html=True)

    # 섹션: 여행 계획 요약 표시
    if 'travel_plan' in st.session_state:
        st.markdown("<div class='section'>", unsafe_allow_html=True)
        st.markdown("<h4 class='subheader'>📜 여행 계획 요약</h4>", unsafe_allow_html=True)

        for key, value in st.session_state.travel_plan.items():
            if isinstance(value, dict):
                st.markdown(f"**{key}**:")
                for subkey, subvalue in value.items():
                    st.markdown(f"- **{subkey}**: {subvalue}")
            elif isinstance(value, list):
                st.markdown(f"**{key}**: {', '.join(value)}")
            else:
                st.markdown(f"**{key}**: {value}")

        st.markdown("</div>", unsafe_allow_html=True)

        # 섹션: 일정 목록
        st.markdown("<div class='section'>", unsafe_allow_html=True)
        st.markdown("<h4 class='subheader'>📋 현재 일정 목록</h4>", unsafe_allow_html=True)

        schedule_df = pd.DataFrame([
            {"날짜": date, "일정": schedule} 
            for date, schedule in st.session_state.travel_plan["일정"].items()
        ])
        st.dataframe(schedule_df, width=700, height=300)
        st.markdown("</div>", unsafe_allow_html=True)

        # 섹션: 일정 추가
        st.markdown("<div class='section'>", unsafe_allow_html=True)
        st.markdown("<h4 class='subheader'>✅ 새로운 일정 추가</h4>", unsafe_allow_html=True)

        add_date = st.selectbox(
            "일정을 추가할 날짜를 선택하세요",
            options=list(st.session_state.travel_plan["일정"].keys()),
            key="add_date"
        )

        st.markdown("**현재 일정:**")
        st.info(st.session_state.travel_plan["일정"][add_date])

        new_schedule = st.text_area(
            "새로운 일정을 입력하세요",
            help="이 날짜에 추가할 새로운 일정을 입력하세요"
        )

        if st.button("✅ 일정 추가"):
            if new_schedule:
                current_schedule = st.session_state.travel_plan["일정"][add_date]
                if current_schedule:
                    st.session_state.travel_plan["일정"][add_date] = f"{current_schedule}, {new_schedule}"
                else:
                    st.session_state.travel_plan["일정"][add_date] = new_schedule

                save_json(st.session_state.travel_plan, "result.json")
                st.success("일정이 추가되었습니다!", icon="✅")
                st.rerun()
            else:
                st.error("새로운 일정을 입력해주세요.", icon="❌")

        st.markdown("</div>", unsafe_allow_html=True)

        # 섹션: 개별 일정 삭제
        st.markdown("<div class='section'>", unsafe_allow_html=True)
        st.markdown("<h4 class='subheader'>🗑️ 일정 삭제</h4>", unsafe_allow_html=True)

        delete_date = st.selectbox(
            "일정을 삭제할 날짜를 선택하세요",
            options=list(st.session_state.travel_plan["일정"].keys()),
            key="delete_date"
        )

        # 선택한 날짜의 일정을 개별 항목으로 분리
        schedules = split_schedule(st.session_state.travel_plan["일정"][delete_date])

        if schedules:
            st.markdown("**현재 일정 목록:**")
            selected_schedules = []

            # 각 일정별로 체크박스 생성
            for schedule in schedules:
                if not st.checkbox(schedule, key=f"delete_{schedule}"):
                    selected_schedules.append(schedule)

            if st.button("🗑️ 선택한 일정 삭제", help="체크한 일정들을 삭제합니다"):
                # 선택되지 않은 일정들만 유지
                st.session_state.travel_plan["일정"][delete_date] = join_schedule(selected_schedules)
                save_json(st.session_state.travel_plan, "result.json")
                st.success("선택한 일정이 삭제되었습니다!", icon="✅")
                st.rerun()
        else:
            st.info("이 날짜에는 삭제할 일정이 없습니다.", icon="ℹ️")

        st.markdown("</div>", unsafe_allow_html=True)

    else:
        st.warning("여행 계획이 로드되지 않았습니다.")
