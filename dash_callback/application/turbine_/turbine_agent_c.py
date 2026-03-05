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

@app.callback(
    Output('chat-history-container', 'children'),
    Input('chat-input', 'nClicksSearch'),  # 监听回车/点击
    State('chat-input', 'value'),
    State('chat-history-container', 'children'),
    State('turbine-session-store', 'data'),
    # prevent_initial_call=True
)
def handle_qa(nClicksSearch, user_input, chat_history, session_data):
    if not nClicksSearch:
        return no_update
    print(f"==== 成功接收到回答点击/回车：{nClicksSearch} ====")

    session_id = session_data.get('session_id', 'default_user_session')
    chat_history = chat_history or []

    if not user_input:
        return no_update

    # 将用户输入立即显示在界面右侧
    chat_history.append(
        html.Div(f"🧑‍🎓 用户: {user_input}", style={'textAlign': 'right', 'margin': '10px', 'color': 'blue'})
    )

    # 🔴 核心融合点：调用 Core 层
    try:
        result = turbine_system.chat(user_input=user_input, session_id=session_id)
        response_text = result.get('response', '系统开小差了')
    except Exception as e:
        print(f"智能问答出错: {e}")
        response_text = f"抱歉，系统发生错误: {str(e)}"

    # 将 AI 回复显示在界面左侧
    chat_history.append(
        html.Div([
            html.Span("🤖 助手: "),
            dcc.Markdown(response_text)
        ], style={'textAlign': 'left', 'margin': '10px', 'backgroundColor': '#f0f2f5', 'padding': '10px',
                  'borderRadius': '5px'})
    )

    return chat_history


@app.callback(
    Output('generate-result-container', 'children'),
    Input('generate-btn', 'nClicks'),
    State('chapter-input', 'value'),
    State('question-type-select', 'value'),
    State('difficulty-select', 'value'),
    State('question-count-input', 'value'),
    # prevent_initial_call=True
)
def handle_generate_questions(nClicks, chapter, q_type, difficulty, count):
    if not nClicks:
        return no_update
    print(f"==== 成功接收到生成题目点击：{nClicks} ====")

    # 🔴 核心融合点：调用 Core 层的出题方法
    try:
        questions = turbine_system.generate_questions(
            chapter=chapter,
            question_type=q_type,
            count=count,
            difficulty=difficulty
        )
    except Exception as e:
        print(f"调用大模型生成题目出错: {e}")
        return fac.AntdAlert(message=f"生成题目失败: {str(e)}", type="error")

    if not questions:
        return fac.AntdAlert(message="大模型未能返回题目，请重试。", type="warning")

    # 🔴 新增：打印结构，防止白屏排查
    print(f"==== 大模型生成的题目数据：{questions} ====")

    # 兼容大模型有时返回 {"questions": [...]} 的情况
    if isinstance(questions, dict) and "questions" in questions:
        questions = questions["questions"]
    if not isinstance(questions, list):
        questions = [questions]  # 如果只返回了一道题的字典，强转为列表

    cards = []
    # 遍历生成的每一道题目，安全提取并渲染
    for i, q in enumerate(questions):
        try:
            # 1. 安全提取文本
            question_text = str(q.get('question', '未提取到题目内容'))
            difficulty_text = str(q.get('difficulty', difficulty))  # 默认使用选择的难度
            answer_text = str(q.get('answer', '略'))
            explanation_text = str(q.get('explanation', '无解析'))

            # 2. 安全提取知识点
            kp = q.get('knowledge_point', '综合知识')
            if isinstance(kp, list):
                kp = "，".join([str(k) for k in kp])
            else:
                kp = str(kp)

            # 3. 安全提取选项 (兼容 list, dict, str)
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

            # 4. 组装安全的卡片 (使用 html.Details)
            card = fac.AntdCard(
                title=f"第 {i + 1} 题 ({difficulty_text})",
                children=[
                    html.P(question_text, style={'fontWeight': 'bold', 'fontSize': '16px'}),
                    html.Div(options_ui, style={'marginBottom': '15px'}),

                    html.Details([
                        html.Summary('👁️ 点击查看答案与解析', style={
                            'cursor': 'pointer',
                            'fontWeight': 'bold',
                            'color': '#1677ff',
                            'userSelect': 'none',
                            'outline': 'none'
                        }),
                        html.Div([
                            html.P(f"【答案】: {answer_text}",
                                   style={'color': 'green', 'fontWeight': 'bold', 'marginTop': '10px'}),
                            html.P(f"【解析】: {explanation_text}", style={'color': '#555'}),
                            fac.AntdTag(content=kp, color='blue')
                        ], style={
                            'padding': '12px',
                            'backgroundColor': '#f5f5f5',
                            'borderRadius': '6px',
                            'marginTop': '10px'
                        })
                    ])
                ],
                style={'marginBottom': '15px', 'boxShadow': '0 2px 8px rgba(0,0,0,0.1)'}
            )
            cards.append(card)
        except Exception as e:
            print(f"渲染第 {i + 1} 题时出错: {e}")
            cards.append(fac.AntdCard(title=f"第 {i + 1} 题渲染失败", children=[html.P(f"数据格式异常: {e}")]))

    return html.Div(cards)


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
    State('upload-standard-answer-file', 'contents'),
    State('upload-standard-answer-file', 'filename'),
    # prevent_initial_call=True
)
def handle_correction(nClicks, question, text_answer, hw_contents, hw_filename, std_contents, std_filename):
    if not nClicks:
        return no_update
    print(f"==== 成功接收到对比点击：{nClicks} ====")

    # 辅助函数 1：解析 Base64 文件并保存为物理临时文件
    def parse_uploaded_file(contents, filename):
        if not contents:
            return None
        content_type, content_string = contents.split(',')
        decoded_bytes = base64.b64decode(content_string)

        ext = os.path.splitext(filename)[1].lower()
        temp_filename = f"upload_{uuid.uuid4().hex}{ext}"
        temp_filepath = os.path.join(tempfile.gettempdir(), temp_filename)

        with open(temp_filepath, "wb") as f:
            f.write(decoded_bytes)

        return {
            "filename": filename,
            "filepath": temp_filepath,
            "ext": ext
        }

    # 🟢 核心新增函数：将 PDF 或 Word 转换为图片列表
    def convert_doc_to_images(filepath, ext):
            image_paths = []
            target_pdf_path = filepath

            # 1. 如果是 Word，先转成 PDF (使用原生 win32com 实现，更稳定)
            if ext in ['.docx', '.doc']:
                if not (pythoncom and win32com):
                    print("未安装 pywin32，无法转换 Word 文档")
                    return []

                target_pdf_path = filepath.rsplit('.', 1)[0] + '.pdf'

                # 必须转换为严格的绝对路径
                abs_filepath = os.path.abspath(filepath)
                abs_target_pdf = os.path.abspath(target_pdf_path)

                word = None
                try:
                    # 声明在当前线程使用 COM
                    pythoncom.CoInitialize()

                    # 🟢 DispatchEx：强制启动一个全新的 Word 独立进程，避免与挂起的僵尸进程冲突
                    word = win32com.client.DispatchEx("Word.Application")
                    word.Visible = False
                    # 🟢 核心：强制关闭所有警告弹窗（如受保护的视图、宏警告等）
                    word.DisplayAlerts = False

                    # 🟢 只读模式打开，防止文件被占用锁死
                    doc = word.Documents.Open(abs_filepath, ReadOnly=True, ConfirmConversions=False)

                    # 17 代表 wdFormatPDF
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
                    # 确保资源释放
                    pythoncom.CoUninitialize()

            # 2. 将 PDF 按页转换为图片
            if target_pdf_path.endswith('.pdf') and os.path.exists(target_pdf_path):
                if not fitz:
                    print("未安装 PyMuPDF(fitz)，无法转换 PDF")
                    return []
                try:
                    # 打开 PDF 文件
                    doc = fitz.open(target_pdf_path)
                    for page_num in range(len(doc)):
                        if page_num >= 10:  # 限制最多转换前 10 页
                            break

                        page = doc.load_page(page_num)
                        pix = page.get_pixmap(dpi=150)
                        img_path = f"{target_pdf_path}_page{page_num}.jpg"
                        pix.save(img_path)
                        image_paths.append(img_path)
                    doc.close()
                except Exception as e:
                    print(f"PDF 转图片失败: {e}")

            return image_paths

    # --- 1. 处理学生作业文件 ---
    student_file_data = parse_uploaded_file(hw_contents, hw_filename)
    student_img_list = []

    if student_file_data:
        ext = student_file_data['ext']
        if ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif']:
            student_img_list.append(student_file_data['filepath'])  # 本身是图片
        elif ext in ['.pdf', '.docx', '.doc']:
            # 转换为图片列表并合并到数组中
            converted_imgs = convert_doc_to_images(student_file_data['filepath'], ext)
            student_img_list.extend(converted_imgs)

    # --- 2. 处理参考答案文件 ---
    standard_file_data = parse_uploaded_file(std_contents, std_filename)
    standard_img_list = []

    if standard_file_data:
        ext = standard_file_data['ext']
        if ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif']:
            standard_img_list.append(standard_file_data['filepath'])
        elif ext in ['.pdf', '.docx', '.doc']:
            converted_imgs = convert_doc_to_images(standard_file_data['filepath'], ext)
            standard_img_list.extend(converted_imgs)

    # --- 3. 调用 Core 层 ---
    try:
        # 现在无论是直接上传的图片，还是由 Word/PDF 转换来的图片，统一都走多模态视觉通道
        result = turbine_system.grade_answer(
            student_answer=text_answer or "",  # 如果用户手填了文本，依然保留
            student_images=student_img_list,
            reference="",  # 参考内容全部转图片了，文本置空
            reference_images=standard_img_list,
            topic=question or ""
        )
        response_text = result.get("response", "批改系统未能返回结果")
    except Exception as e:
        print(f"作业批改调用出错: {e}")
        response_text = f"批改失败，系统抛出异常: {str(e)}"

    return html.Div([
        html.H4("批改与对比结果：", style={'color': '#cf1322'}),
        dcc.Markdown(response_text)
    ], style={'padding': '20px', 'backgroundColor': '#fff2f0', 'border': '1px solid #ffa39e', 'borderRadius': '8px'})
