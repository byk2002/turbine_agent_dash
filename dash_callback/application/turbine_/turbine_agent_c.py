# src/dash_callback/application/turbine_/turbine_agent_c.py
import base64
from dash import Input, Output, State, html, dcc, no_update
from config.dashgo_conf import app
from common.turbine_core.instance import turbine_system

# ... [保留前面的 handle_chat 和 handle_generate_questions 回调] ...

# 提示已上传的学生作业文件名
@app.callback(
    Output('upload-status-tip', 'children'),
    Input('upload-homework-file', 'filename'),
    prevent_initial_call=True
)
def update_homework_status(filename):
    if filename:
        return f"✅ 学生作业: {filename}"
    return ""

# 提示已上传的参考答案文件名
@app.callback(
    Output('upload-standard-status-tip', 'children'),
    Input('upload-standard-answer-file', 'filename'),
    prevent_initial_call=True
)
def update_standard_status(filename):
    if filename:
        return f"✅ 参考答案: {filename}"
    return ""

# 作业批改（结合双文件对比：学生作业 vs 参考答案）回调
@app.callback(
    Output('correction-result-container', 'children'),
    Input('correct-btn', 'nClicks'),
    State('correction-question-input', 'value'),
    State('correction-answer-input', 'value'),
    State('upload-homework-file', 'contents'),
    State('upload-homework-file', 'filename'),
    State('upload-standard-answer-file', 'contents'),    # 新增：参考答案内容
    State('upload-standard-answer-file', 'filename'),    # 新增：参考答案文件名
    prevent_initial_call=True
)
def handle_correction(n_clicks, question, text_answer, hw_contents, hw_filename, std_contents, std_filename):
    if not n_clicks:
        return no_update
        
    # 辅助函数：解析 Base64 文件
    def parse_uploaded_file(contents, filename):
        if not contents:
            return None
        content_type, content_string = contents.split(',')
        decoded_bytes = base64.b64decode(content_string)
        return {
            "filename": filename,
            "content_type": content_type,
            "bytes": decoded_bytes,
            "base64_str": content_string
        }
        
    # 1. 解析学生作业文件
    student_file_data = parse_uploaded_file(hw_contents, hw_filename)
    
    # 2. 解析参考答案文件
    standard_file_data = parse_uploaded_file(std_contents, std_filename)
    
    # 将题目、学生文本解答、学生文件、参考答案文件统一交给底层大模型
    # 注：你需要在 turbine_system.correct_homework 的底层实现中处理 standard_file_data 参数，让大模型阅读它作为判断标准
    result = turbine_system.correct_homework(
        original_question=question,
        student_text_answer=text_answer,
        student_file_data=student_file_data,
        standard_file_data=standard_file_data # 传入参考答案
    )
    
    response_text = result.get("response", "批改失败或系统异常")
    
    return html.Div([
        html.H4("批改与对比结果：", style={'color': '#cf1322'}),
        dcc.Markdown(response_text)
    ], style={'padding': '20px', 'backgroundColor': '#fff2f0', 'border': '1px solid #ffa39e', 'borderRadius': '8px'})
