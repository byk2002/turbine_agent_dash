# src/dash_callback/application/turbine_/turbine_agent_c.py
from dash import Input, Output, State, html
from config.dashgo_conf import app
from common.turbine_core.instance import turbine_system


@app.callback(
    Output('generate-result-container', 'children'),
    Input('generate-btn', 'nClicks'),
    State('chapter-input', 'value'),
    State('question-type-select', 'value'),
    State('difficulty-select', 'value'),  # <--- 新增获取难度
    State('question-count-input', 'value'),  # <--- 新增获取数量
    prevent_initial_call=True
)
def handle_chat(n_clicks, user_input, session_data):
    if not user_input:
        return dash.no_update

    session_id = session_data.get('session_id')

    # 调用底层 Agent (对应原 Streamlit 中的 agent.chat)
    result = turbine_system.chat(user_input, session_id=session_id)
    response_text = result.get("response", "系统异常")

    # 构造并返回渲染后的气泡组件（此处简化，实际可维护一个历史列表状态）
    return html.Div([
        html.P(f"👤 用户: {user_input}"),
        html.P(f"🤖 助手: {response_text}")
    ])


@app.callback(
    Output('generate-result-container', 'children'),
    Input('generate-btn', 'nClicks'),
    State('chapter-input', 'value'),
    State('question-type-select', 'value'),
    State('difficulty-select', 'value'),  # <--- 新增获取难度
    State('question-count-input', 'value'),  # <--- 新增获取数量
    prevent_initial_call=True
)
def handle_generate_questions(n_clicks, chapter, q_type, difficulty, count):
    # 调用底层出题接口
    result = turbine_system.generate_questions(
        chapter=chapter,
        question_type=q_type,
        count=count,
        difficulty=difficulty
    )
    return dcc.Markdown(result.get("response", "生成失败"))
