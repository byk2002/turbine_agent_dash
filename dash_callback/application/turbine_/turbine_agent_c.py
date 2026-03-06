# src/dash_callback/application/turbine_/turbine_agent_c.py
import base64
import os
import tempfile
import uuid
from dash import Input, Output, State, html, dcc, no_update
from server import app
from common.turbine_core.instance import turbine_system
import feffery_antd_components as fac

# 尝试导入文档转换库
try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None
    print("⚠️ 警告: 缺少 PyMuPDF，请运行 pip install PyMuPDF 以支持 PDF转图片")

try:
    import pythoncom
    import win32com.client
except ImportError:
    pythoncom = None
    win32com = None
    print("⚠️ 警告: 缺少 pywin32，请运行 pip install pywin32")

# 🟢 新增：导入 pythoncom 用于多线程 COM 初始化
try:
    import pythoncom
except ImportError:
    pythoncom = None


# ==========================================
# 回调 1：智能问答 (双输出：结果上屏 + 清空输入框)
# ==========================================
@app.callback(
    [Output('chat-history-container', 'children'),
     Output('chat-input', 'value')],
    Input('chat-input', 'nClicksSearch'),
    State('chat-input', 'value'),
    State('chat-history-container', 'children'),
    State('turbine-session-store', 'data'),
    prevent_initial_call=True
)
def handle_qa(nClicksSearch, user_input, chat_history, session_data):
    if not nClicksSearch or not user_input:
        return no_update, no_update

    print(f"==== 成功接收到回答点击/回车：{nClicksSearch} ====")

    chat_history = chat_history or []
    if not isinstance(chat_history, list):
        chat_history = [chat_history]

    session_id = session_data.get('session_id', 'default_user_session') if session_data else 'default_user_session'

    try:
        result = turbine_system.ask_question(question=user_input, session_id=session_id)
        response_text = result.get('response', '系统开小差了')
    except Exception as e:
        print(f"智能问答出错: {e}")
        response_text = f"抱歉，系统发生错误: {str(e)}"

    chat_group = html.Div([
        html.Div(f"🧑‍🎓 用户: {user_input}", style={
            'textAlign': 'right', 'margin': '10px 0', 'color': '#1677ff', 'fontWeight': 'bold'
        }),
        html.Div([
            html.Span("🤖 助手: ", style={'fontWeight': 'bold', 'color': '#52c41a'}),
            html.Div(
                dcc.Markdown(response_text, mathjax=True),
                style={'marginTop': '8px'}
            )
        ], style={
            'textAlign': 'left', 'margin': '10px 0 20px 0', 'backgroundColor': '#f6ffed',
            'border': '1px solid #b7eb8f', 'padding': '12px', 'borderRadius': '8px'
        })
    ])

    chat_history.insert(0, chat_group)
    return chat_history, None


# ==========================================
# 回调 2：生成练习题 (单输出：渲染结果区域)
# ==========================================
@app.callback(
    Output('generate-result-container', 'children'),
    Input('generate-btn', 'nClicks'),
    State('chapter-input', 'value'),
    State('question-type-select', 'value'),
    State('difficulty-select', 'value'),
    State('question-count-input', 'value'),
    prevent_initial_call=True
)
def handle_generate_questions(nClicks, chapter, q_type, difficulty, count):
    if not nClicks:
        return no_update
    print(f"==== 成功接收到生成题目点击：{nClicks} ====")

    try:
        questions = turbine_system.generate_questions(
            chapter=chapter,
            question_type=q_type,
            count=count,
            difficulty=difficulty
        )
    except Exception as e:
        return fac.AntdAlert(message=f"生成题目失败: {str(e)}", type="error")

    if not questions:
        return fac.AntdAlert(message="大模型未能返回题目，请重试。", type="warning")

    if isinstance(questions, dict) and "questions" in questions:
        questions = questions["questions"]
    if not isinstance(questions, list):
        questions = [questions]

    cards = []
    for i, q in enumerate(questions):
        try:
            question_text = str(q.get('question', '未提取到题目内容'))
            difficulty_text = str(q.get('difficulty', difficulty))
            answer_text = str(q.get('answer', '略'))
            explanation_text = str(q.get('explanation', '无解析'))

            kp = q.get('knowledge_point', '综合知识')
            if isinstance(kp, list):
                kp = "，".join([str(k) for k in kp])
            else:
                kp = str(kp)

            options_ui = []
            raw_options = q.get('options') or q.get('option') or []

            if isinstance(raw_options, list):
                for opt in raw_options:
                    options_ui.append(html.Div(str(opt), style={'marginLeft': '20px', 'padding': '5px 0'}))
            elif isinstance(raw_options, dict):
                for k, v in raw_options.items():
                    options_ui.append(html.Div(f"{k}: {v}", style={'marginLeft': '20px', 'padding': '5px 0'}))
            elif raw_options:
                options_ui.append(html.Div(str(raw_options), style={'marginLeft': '20px', 'padding': '5px 0'}))

            card = fac.AntdCard(
                title=f"第 {i + 1} 题 ({difficulty_text})",
                children=[
                    html.P(question_text, style={'fontWeight': 'bold', 'fontSize': '16px'}),
                    html.Div(options_ui, style={'marginBottom': '15px'}),
                    html.Details([
                        html.Summary('👁️ 点击查看答案与解析', style={
                            'cursor': 'pointer', 'fontWeight': 'bold', 'color': '#1677ff', 'outline': 'none'
                        }),
                        html.Div([
                            html.P(f"【答案】: {answer_text}", style={'color': 'green', 'fontWeight': 'bold', 'marginTop': '10px'}),
                            html.P(f"【解析】: {explanation_text}", style={'color': '#555'}),
                            fac.AntdTag(content=kp, color='blue')
                        ], style={'padding': '12px', 'backgroundColor': '#f5f5f5', 'borderRadius': '6px', 'marginTop': '10px'})
                    ])
                ],
                style={'marginBottom': '15px', 'boxShadow': '0 2px 8px rgba(0,0,0,0.1)'}
            )
            cards.append(card)
        except Exception as e:
            cards.append(fac.AntdCard(title=f"第 {i + 1} 题渲染失败", children=[html.P(f"数据格式异常: {e}")]))

    return html.Div(cards)


# ==========================================
# 回调 3 & 4：文件上传状态提示
# ==========================================
@app.callback(
    Output('upload-status-tip', 'children'),
    Input('upload-homework-file', 'filename'),
    prevent_initial_call=True
)
def update_homework_status(filename):
    if filename: return f"✅ 学生作业: {filename}"
    return ""

@app.callback(
    Output('upload-standard-status-tip', 'children'),
    Input('upload-standard-answer-file', 'filename'),
    prevent_initial_call=True
)
def update_standard_status(filename):
    if filename: return f"✅ 参考答案: {filename}"
    return ""


# ==========================================
# 回调 5：作业批改 (多输出：渲染结果 + 清空所有输入与文件)
# ==========================================
@app.callback(
    [
        Output('correction-result-container', 'children'),
        Output('correction-question-input', 'value'),  # 清空题目输入框
        Output('correction-answer-input', 'value'),  # 清空文本答案输入框
        Output('upload-homework-file', 'contents'),  # 清空学生作业文件内容
        Output('upload-homework-file', 'filename'),  # 清空学生作业文件名
        Output('upload-standard-answer-file', 'contents'),  # 清空参考答案文件内容
        Output('upload-standard-answer-file', 'filename')  # 清空参考答案文件名
    ],
    Input('correct-btn', 'nClicks'),
    State('correction-question-input', 'value'),
    State('correction-answer-input', 'value'),
    State('upload-homework-file', 'contents'),
    State('upload-homework-file', 'filename'),
    State('upload-standard-answer-file', 'contents'),
    State('upload-standard-answer-file', 'filename'),
    State('turbine-session-store', 'data'),
    prevent_initial_call=True
)
def handle_correction(nClicks, question, text_answer, hw_contents, hw_filename, std_contents, std_filename,
                      session_data):
    if not nClicks:
        # 如果未点击，保持 7 个输出都不更新
        return no_update, no_update, no_update, no_update, no_update, no_update, no_update

    print(f"==== 成功接收到对比点击：{nClicks} ====")

    session_id = session_data.get('session_id', 'default_user_session') if session_data else 'default_user_session'

    def parse_uploaded_file(contents, filename):
        if not contents: return None
        content_type, content_string = contents.split(',')
        decoded_bytes = base64.b64decode(content_string)
        ext = os.path.splitext(filename)[1].lower()
        temp_filename = f"upload_{uuid.uuid4().hex}{ext}"
        temp_filepath = os.path.join(tempfile.gettempdir(), temp_filename)
        with open(temp_filepath, "wb") as f:
            f.write(decoded_bytes)
        return {"filename": filename, "filepath": temp_filepath, "ext": ext}

    def convert_doc_to_images(filepath, ext):
        image_paths = []
        target_pdf_path = filepath
        if ext in ['.docx', '.doc']:
            if not (pythoncom and win32com): return []
            target_pdf_path = filepath.rsplit('.', 1)[0] + '.pdf'
            abs_filepath = os.path.abspath(filepath)
            abs_target_pdf = os.path.abspath(target_pdf_path)
            word = None
            try:
                pythoncom.CoInitialize()
                word = win32com.client.DispatchEx("Word.Application")
                word.Visible = False
                word.DisplayAlerts = False
                doc = word.Documents.Open(abs_filepath, ReadOnly=True, ConfirmConversions=False)
                doc.SaveAs(abs_target_pdf, FileFormat=17)
                doc.Close()
            except Exception as e:
                print(f"原生 Word 转 PDF 报错: {e}")
                return []
            finally:
                if word:
                    try:
                        word.Quit()
                    except:
                        pass
                pythoncom.CoUninitialize()

        if target_pdf_path.endswith('.pdf') and os.path.exists(target_pdf_path):
            if not fitz: return []
            try:
                doc = fitz.open(target_pdf_path)
                for page_num in range(len(doc)):
                    if page_num >= 10: break
                    page = doc.load_page(page_num)
                    pix = page.get_pixmap(dpi=150)
                    img_path = f"{target_pdf_path}_page{page_num}.jpg"
                    pix.save(img_path)
                    image_paths.append(img_path)
                doc.close()
            except Exception as e:
                print(f"PDF 转图片失败: {e}")
        return image_paths

    student_file_data = parse_uploaded_file(hw_contents, hw_filename)
    student_img_list = []
    if student_file_data:
        ext = student_file_data['ext']
        if ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif']:
            student_img_list.append(student_file_data['filepath'])
        elif ext in ['.pdf', '.docx', '.doc']:
            student_img_list.extend(convert_doc_to_images(student_file_data['filepath'], ext))

    standard_file_data = parse_uploaded_file(std_contents, std_filename)
    standard_img_list = []
    if standard_file_data:
        ext = standard_file_data['ext']
        if ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif']:
            standard_img_list.append(standard_file_data['filepath'])
        elif ext in ['.pdf', '.docx', '.doc']:
            standard_img_list.extend(convert_doc_to_images(standard_file_data['filepath'], ext))

    try:
        result = turbine_system.grade_answer(
            student_answer=text_answer or "",
            student_images=student_img_list,
            reference="",
            reference_images=standard_img_list,
            topic=question or "",
            session_id=session_id
        )
        response_text = result.get("response", "批改系统未能返回结果")
    except Exception as e:
        print(f"作业批改调用出错: {e}")
        response_text = f"批改失败，系统抛出异常: {str(e)}"

    # 渲染结果的 UI 组件
    result_ui = html.Div([
        html.H4("批改与对比结果：", style={'color': '#cf1322'}),
        dcc.Markdown(response_text, mathjax=True)  # 同样开启 mathjax 防止公式渲染报错
    ], style={'padding': '20px', 'backgroundColor': '#fff2f0', 'border': '1px solid #ffa39e', 'borderRadius': '8px'})

    # 返回 7 个值：第 1 个更新结果面板，后 6 个 None 用于物理清空所有的文本框和文件上传组件
    return result_ui, None, None, None, None, None, None
