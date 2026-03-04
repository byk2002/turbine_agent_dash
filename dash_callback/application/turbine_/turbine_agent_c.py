# src/dash_callback/application/turbine_/turbine_agent_c.py
import base64
from dash import Input, Output, State, html, dcc, no_update
from config.dashgo_conf import app
from common.turbine_core.instance import turbine_system
import feffery_antd_components as fac

@app.callback(
    Output('correction-result-container', 'children'),
    Input('correct-btn', 'nClicks'),
    State('correction-question-input', 'value'),
    State('correction-answer-input', 'value'),
    State('upload-homework-file', 'contents'),
    State('upload-homework-file', 'filename'),
    State('upload-standard-answer-file', 'contents'),
    State('upload-standard-answer-file', 'filename'),
    State('turbine-session-store', 'data'), # 获取 session_id
    prevent_initial_call=True
)
def handle_correction(n_clicks, question, text_answer, hw_contents, hw_filename, std_contents, std_filename, session_data):
    if not n_clicks:
        return no_update
        
    session_id = session_data.get('session_id', 'default_user_session')
    
    # 辅助函数：解析 Base64 文件
    def parse_uploaded_file(contents, filename):
        if not contents:
            return None
        content_type, content_string = contents.split(',')
        return {
            "filename": filename,
            "content_type": content_type,
            "bytes": base64.b64decode(content_string),
            "base64_str": content_string
        }
        
    student_file_data = parse_uploaded_file(hw_contents, hw_filename)
    standard_file_data = parse_uploaded_file(std_contents, std_filename)
    
    # 调用后端接口 (需确保此方法底层传递了 session_id)
    result = turbine_system.correct_homework(
        session_id=session_id,
        original_question=question,
        student_text_answer=text_answer,
        student_file_data=student_file_data,
        standard_file_data=standard_file_data
    )
    
    # === 提取结构化打分与画像数据 ===
    grading = result.get("grading", {})
    user_profile = result.get("user_profile", {})
    response_text = result.get("response", "批改完成")
    
    score = grading.get("score", 0)
    level = grading.get("level", "未评级")
    feedback = grading.get("feedback", "暂无反馈")
    correct_points = grading.get("correct_points", [])
    wrong_points = grading.get("wrong_points", [])
    
    elo_rating = user_profile.get("elo_rating", 1200)
    skill_level = user_profile.get("skill_level", "beginner")
    
    # 若无评分详情（例如解析失败），兜底显示纯文本
    if score == -1 or not grading:
        return html.Div([
            fac.AntdAlert(message="批改解析异常，显示原始文本", type="warning", showIcon=True),
            dcc.Markdown(response_text)
        ])

    # === 构造结构化的交互式反馈面板 ===
    return html.Div([
        # 1. 顶部统计数据行 (得分、Elo、等级)
        fac.AntdCard(
            fac.AntdRow(
                gutter=16,
                children=[
                    fac.AntdCol(
                        fac.AntdStatistic(title="本次得分", value=score, suffix="分", valueStyle={'color': '#cf1322' if score < 60 else '#3f8600'}),
                        span=6
                    ),
                    fac.AntdCol(
                        fac.AntdStatistic(title="作业评级", value=level),
                        span=6
                    ),
                    fac.AntdCol(
                        fac.AntdStatistic(title="当前 Elo 战力", value=elo_rating, suffix="🏆"),
                        span=6
                    ),
                    fac.AntdCol(
                        html.Div([
                            html.Div("能力定级", style={'color': '#888', 'fontSize': '14px', 'marginBottom': '4px'}),
                            fac.AntdTag(content=skill_level.upper(), color="blue", style={'fontSize': '16px', 'padding': '4px 10px'})
                        ]),
                        span=6
                    ),
                ]
            ),
            style={'marginBottom': '20px', 'backgroundColor': '#fafafa'}
        ),
        
        # 2. 总体评价
        fac.AntdCard(
            title="总体评价",
            headStyle={'fontWeight': 'bold'},
            children=fac.AntdParagraph(feedback),
            style={'marginBottom': '20px'}
        ),
        
        # 3. 具体得分点与失分点对比
        fac.AntdRow(
            gutter=16,
            children=[
                fac.AntdCol(
                    fac.AntdCard(
                        title=fac.AntdSpace([fac.AntdIcon(icon="antd-check-circle", style={'color': '#52c41a'}), "正确知识点"]),
                        children=[fac.AntdText(f"✅ {cp}", style={'display': 'block', 'marginBottom': '5px'}) for cp in correct_points] if correct_points else "暂无",
                        style={'borderColor': '#b7eb8f', 'backgroundColor': '#f6ffed', 'height': '100%'}
                    ),
                    span=12
                ),
                fac.AntdCol(
                    fac.AntdCard(
                        title=fac.AntdSpace([fac.AntdIcon(icon="antd-close-circle", style={'color': '#f5222d'}), "需要改进/错误点"]),
                        children=[fac.AntdText(f"❌ {wp}", style={'display': 'block', 'marginBottom': '5px'}) for wp in wrong_points] if wrong_points else "暂无",
                        style={'borderColor': '#ffa39e', 'backgroundColor': '#fff2f0', 'height': '100%'}
                    ),
                    span=12
                )
            ]
        ),
        
        # 4. 改进建议折叠面板
        html.Div(
            fac.AntdCollapse(
                items=[{
                    'key': 'suggestions',
                    'label': '💡 点击查看改进建议与参考答案',
                    'children': html.Div([
                        html.H5("改进建议："),
                        html.Ul([html.Li(s) for s in grading.get('suggestions', [])]),
                        html.H5("参考答案：", style={'marginTop': '15px'}),
                        dcc.Markdown(grading.get('reference_answer', '无'))
                    ])
                }]
            ),
            style={'marginTop': '20px'}
        )
    ])


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

