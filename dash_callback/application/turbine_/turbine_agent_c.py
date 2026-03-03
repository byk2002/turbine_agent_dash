# src/dash_callback/application/turbine_/turbine_agent_c.py
import base64
from dash import Input, Output, State, html, dcc, no_update
from config.dashgo_conf import app
from common.turbine_core.instance import turbine_system

# 1. 聊天问答回调
@app.callback(
    Output('chat-history-container', 'children'),
    Input('chat-input', 'nClicksSearch'), # 监听搜索模式的回车和点击
    Input('chat-input', 'nSubmit'),
    State('chat-input', 'value'),
    State('turbine-session-store', 'data'),
    prevent_initial_call=True
)
def handle_chat(n_clicks_search, n_submit, user_input, session_data):
    if not user_input:
        return no_update

    session_id = session_data.get('session_id')
    result = turbine_system.chat(user_input, session_id=session_id)
    response_text = result.get("response", "系统异常")

    return html.Div([
        html.P(f"👤 用户: {user_input}", style={'fontWeight': 'bold', 'color': '#1677ff'}),
        html.Div(dcc.Markdown(response_text), style={'backgroundColor': '#f5f5f5', 'padding': '10px', 'borderRadius': '5px'})
    ])

# 2. 生成题目回调
@app.callback(
    Output('generate-result-container', 'children'),
    Input('generate-btn', 'nClicks'),
    State('chapter-input', 'value'),
    State('question-type-select', 'value'),
    State('difficulty-select', 'value'),
    State('question-count-input', 'value'),
    prevent_initial_call=True
)
def handle_generate_questions(n_clicks, chapter, q_type, difficulty, count):
    if not n_clicks:
        return no_update
        
    # 将新的参数（难度、数量）传给底层接口
    result = turbine_system.generate_questions(
        chapter=chapter,
        question_type=q_type,
        count=count,
        difficulty=difficulty
    )
    return html.Div(dcc.Markdown(result.get("response", "生成失败")), style={'padding': '15px', 'border': '1px solid #e8e8e8', 'borderRadius': '8px'})

# 3. 提示已上传的文件名
@app.callback(
    Output('upload-status-tip', 'children'),
    Input('upload-homework-file', 'filename'),
    prevent_initial_call=True
)
def update_upload_status(filename):
    if filename:
        return f"✅ 成功加载文件: {filename}"
    return ""

# 4. 新增：作业批改（结合多模态文件上传）回调
@app.callback(
    Output('correction-result-container', 'children'),
    Input('correct-btn', 'nClicks'),
    State('correction-question-input', 'value'),
    State('correction-answer-input', 'value'),
    State('upload-homework-file', 'contents'),
    State('upload-homework-file', 'filename'),
    prevent_initial_call=True
)
def handle_correction(n_clicks, question, text_answer, file_contents, filename):
    if not n_clicks:
        return no_update
        
    file_data = None
    if file_contents:
        # file_contents 格式通常为: "data:application/pdf;base64,JVBERi0xLjQK..."
        content_type, content_string = file_contents.split(',')
        # 解码 base64
        decoded_bytes = base64.b64decode(content_string)
        file_data = {
            "filename": filename,
            "content_type": content_type,
            "bytes": decoded_bytes,
            "base64_str": content_string
        }
    
    # 将获取到的题目、学生文本解答、以及学生上传的文件（图片/PDF）统一交给大模型处理
    # 注意：此处你需要根据你底层 turbine_system 的实际 API 结构来传递这些参数。
    # 比如如果你的 agent 支持 vision/multimodal，你可以把 base64_str 传进去。
    result = turbine_system.correct_homework(
        original_question=question,
        student_text_answer=text_answer,
        student_file_data=file_data # 将文件数据传递给底层核心处理
    )
    
    response_text = result.get("response", "批改失败")
    
    return html.Div([
        html.H4("批改结果：", style={'color': '#cf1322'}),
        dcc.Markdown(response_text)
    ], style={'padding': '20px', 'backgroundColor': '#fff2f0', 'border': '1px solid #ffa39e', 'borderRadius': '8px'})
