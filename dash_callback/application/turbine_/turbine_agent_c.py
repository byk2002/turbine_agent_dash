# src/dash_callback/application/turbine_/turbine_agent_c.py
import base64
import os
import tempfile
import uuid
from dash import Input, Output, State, html, dcc, no_update
from server import app
from common.turbine_core.instance import turbine_system
import feffery_antd_components as fac
from dash import ctx
from dash.dependencies import ALL
import json
import os, json, glob

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
# 🟢 回调 1：智能问答 (多用户历史隔离 + 持久化 + 气泡UI)
# ==========================================
@app.callback(
    [Output('chat-history-store', 'data'),
     Output('chat-history-container', 'children'),
     Output('chat-input', 'value')],
    [Input('chat-input', 'nClicksSearch'),
     Input('clear-chat-btn', 'nClicks')],
    [State('chat-input', 'value'),
     State('chat-history-store', 'data'),
     State('turbine-session-store', 'data')],
    prevent_initial_call=False
)
def handle_qa_and_history(nClicksSearch, clearClicks, user_input, chat_store, session_data):
    ctx_id = ctx.triggered_id

    # 1. 初始化整个存储字典
    chat_store = chat_store or {}
    # 如果本地缓存里有以前旧版本残留的列表数据，直接清空重置为字典，防止报错
    if isinstance(chat_store, list):
        chat_store = {}

    # 获取当前用户的 session_id (即用户名)
    session_id = session_data.get('session_id', 'default_user_session') if session_data else 'default_user_session'

    # 2. 从字典中提取当前专属用户的历史记录
    user_history = chat_store.get(session_id, [])

    # 动作 A: 触发了“清空历史”按钮
    if ctx_id == 'clear-chat-btn':
        # 尝试调用大模型底层的记忆清理接口（如果有）
        if hasattr(turbine_system, 'clear_memory'):
            try:
                turbine_system.clear_memory(session_id)
            except Exception:
                pass

        # 仅清空当前用户的记录，并存回字典
        chat_store[session_id] = []
        return chat_store, [], None

    # 动作 B: 用户发送了新消息
    if ctx_id == 'chat-input' and user_input:
        print(f"==== 接收到 {session_id} 的问题：{user_input} ====")
        try:
            result = turbine_system.ask_question(question=user_input, session_id=session_id)
            response_text = result.get('response', '系统开小差了')
        except Exception as e:
            print(f"智能问答出错: {e}")
            response_text = f"抱歉，系统发生错误: {str(e)}"

        # 将新对话追加到当前用户的列表中
        user_history.append({'role': 'user', 'content': user_input})
        user_history.append({'role': 'assistant', 'content': response_text})

        # 将更新后的专属列表写回大字典
        chat_store[session_id] = user_history

    # 动作 C: 遍历【当前用户】的历史记录并生成 UI
    chat_ui = []
    for msg in user_history:
        if msg['role'] == 'user':
            chat_ui.append(
                html.Div(
                    html.Div([
                        html.Span("🧑‍🎓 我", style={'fontSize': '12px', 'color': '#8c8c8c', 'marginBottom': '4px',
                                                   'display': 'block', 'textAlign': 'right'}),
                        html.Div(msg['content'], style={
                            'display': 'inline-block', 'backgroundColor': '#1677ff', 'color': '#fff',
                            'padding': '10px 14px', 'borderRadius': '12px 0 12px 12px', 'maxWidth': '85%',
                            'textAlign': 'left', 'wordBreak': 'break-word', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
                        })
                    ], style={'textAlign': 'right', 'margin': '10px 0', 'alignSelf': 'flex-end'})
                )
            )
        else:
            chat_ui.append(
                html.Div(
                    html.Div([
                        html.Span("🤖 智能助手", style={'fontSize': '12px', 'color': '#8c8c8c', 'marginBottom': '4px',
                                                       'display': 'block'}),
                        html.Div(dcc.Markdown(msg['content'], mathjax=True), style={
                            'display': 'inline-block', 'backgroundColor': '#ffffff', 'color': '#333',
                            'padding': '10px 14px', 'borderRadius': '0 12px 12px 12px', 'maxWidth': '85%',
                            'border': '1px solid #e8e8e8', 'boxShadow': '0 2px 4px rgba(0,0,0,0.05)',
                            'textAlign': 'left', 'wordBreak': 'break-word'
                        })
                    ], style={'textAlign': 'left', 'margin': '10px 0', 'alignSelf': 'flex-start'})
                )
            )

    new_input_val = None if ctx_id == 'chat-input' else no_update

    # 返回更新后的大字典 chat_store 给前端缓存
    return chat_store, chat_ui, new_input_val

# ==========================================
# 🟢 新增回调：收到新消息时，聊天窗口自动滑倒最底部
# ==========================================
app.clientside_callback(
    """
    function(children) {
        var container = document.getElementById('chat-history-container');
        if (container) {
            // 设置延迟保证新元素已经完全渲染
            setTimeout(function() {
                container.scrollTop = container.scrollHeight;
            }, 100);
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output('chat-scroll-dummy', 'children'),
    Input('chat-history-container', 'children'),
    prevent_initial_call=False
)
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


# ==========================================
# 回调 6 & 7：知识库综合管理 (上传、刷新、动态删除)
# ==========================================
@app.callback(
    [Output('kb-upload-status', 'children'),
     Output('kb-document-list-container', 'children')],
    Input('kb-upload-file', 'contents'),
    Input('kb-refresh-btn', 'nClicks'),
    Input({'type': 'kb-delete-btn', 'index': ALL}, 'confirmCounts'),
    State('kb-upload-file', 'filename'),
    prevent_initial_call=False
)
def handle_kb_management(contents, refresh_clicks, delete_counts, filename):
    print("========== [DEBUG] 回调被触发: handle_kb_management ==========")
    triggered_id = ctx.triggered_id

    # 默认状态：不更新上传提示区域
    status_update = no_update

    # ------------------------------------------
    # 1. 处理文件上传逻辑
    # ------------------------------------------
    if triggered_id == 'kb-upload-file' and contents:
        try:
            content_type, content_string = contents.split(',')
            decoded_bytes = base64.b64decode(content_string)

            save_dir = os.path.join(os.getcwd(), "user_data", "knowledge_base")
            os.makedirs(save_dir, exist_ok=True)
            save_path = os.path.join(save_dir, filename)

            with open(save_path, "wb") as f:
                f.write(decoded_bytes)

            turbine_system.kb_adapter.add_document(save_path)
            # 上传成功，更新提示文字
            status_update = html.Span(f"✅ 文件 {filename} 已成功保存至本地并加入知识库！",
                                      style={'color': '#52c41a', 'fontWeight': 'bold'})
        except Exception as e:
            print(f"知识库添加文件失败: {e}")
            status_update = html.Span(f"❌ 文件 {filename} 添加失败: {str(e)}", style={'color': '#cf1322'})

    # ------------------------------------------
    # 2. 处理文件删除逻辑
    # ------------------------------------------
    elif triggered_id and isinstance(triggered_id, dict) and triggered_id.get('type') == 'kb-delete-btn':
        is_confirmed = False
        for t in ctx.triggered:
            if 'confirmCounts' in t['prop_id'] and t.get('value'):
                is_confirmed = True
                break

        if is_confirmed:
            encoded_path = triggered_id['index']
            file_path_to_delete = base64.b64decode(encoded_path).decode('utf-8')

            print(f"!!! 准备执行删除，目标文件: {file_path_to_delete} !!!")
            try:
                adapter = turbine_system.kb_adapter if hasattr(turbine_system, 'kb_adapter') else turbine_system
                adapter.delete_document(file_path_to_delete)

                # ==========================================
                # 🟢 终极“幽灵记录”抹除术（内存 + 硬盘 + 物理文件三杀）
                # ==========================================
                def scrub_memory_dict(target_dict):
                    if not isinstance(target_dict, dict): return
                    zombie_keys = [k for k in target_dict.keys() if
                                   isinstance(k, str) and k.lower() == file_path_to_delete.lower()]
                    for zk in zombie_keys:
                        target_dict.pop(zk, None)
                        print(f"🔧 内存清理：已成功抹除底层字典键名 -> {zk}")

                docs_info = adapter.list_documents()
                for key_name in ['documents', 'doc_metadata', 'file_hashes']:
                    if isinstance(docs_info, dict) and key_name in docs_info:
                        scrub_memory_dict(docs_info[key_name])

                for attr_name in dir(adapter):
                    if attr_name.startswith('__'): continue
                    try:
                        attr_val = getattr(adapter, attr_name)
                        if isinstance(attr_val, dict):
                            scrub_memory_dict(attr_val)
                            for key_name in ['documents', 'doc_metadata', 'file_hashes']:
                                if key_name in attr_val and isinstance(attr_val[key_name], dict):
                                    scrub_memory_dict(attr_val[key_name])
                    except Exception:
                        pass

                for save_func in ['save_metadata', '_save_metadata', 'save', 'persist']:
                    if hasattr(adapter, save_func):
                        try:
                            getattr(adapter, save_func)()
                        except Exception:
                            pass

                kb_dir = os.path.join(os.getcwd(), "user_data", "knowledge_base")
                upload_dir = os.path.join(os.getcwd(), "user_data", "kb_uploads")

                for target_dir in [kb_dir, upload_dir]:
                    if not os.path.exists(target_dir): continue
                    for jf in glob.glob(os.path.join(target_dir, "*.json")):
                        try:
                            with open(jf, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                            modified = False

                            if isinstance(data, dict):
                                for root_key in ['documents', 'doc_metadata', 'file_hashes']:
                                    if root_key in data and isinstance(data[root_key], dict):
                                        d_dict = data[root_key]
                                        zombie_keys = [k for k in d_dict.keys() if
                                                       k.lower() == file_path_to_delete.lower()]
                                        for zk in zombie_keys:
                                            d_dict.pop(zk, None)
                                            modified = True

                            if modified:
                                with open(jf, 'w', encoding='utf-8') as f:
                                    json.dump(data, f, ensure_ascii=False, indent=4)
                                print(f"🔨 硬盘清理：已物理修改 JSON 切断复活 -> {os.path.basename(jf)}")
                        except Exception as e:
                            print(f"JSON 修改错误: {e}")

                try:
                    if os.path.exists(file_path_to_delete):
                        os.remove(file_path_to_delete)
                        print(f"🗑️ 物理文件清理：已彻底删除源文件 -> {file_path_to_delete}")

                    base_name = os.path.basename(file_path_to_delete)
                    for target_dir in [kb_dir, upload_dir]:
                        if os.path.exists(target_dir):
                            for f in os.listdir(target_dir):
                                if f.lower() == base_name.lower():
                                    full_path = os.path.join(target_dir, f)
                                    os.remove(full_path)
                                    print(f"🗑️ 物理文件清理：已彻底删除源文件 -> {full_path}")
                except Exception as e:
                    print(f"⚠️ 物理文件删除失败 (可能文件被占用): {e}")

                print(f"✅ 文件已成功彻底删除")

                # 🟢 修复核心：文件删除成功后，清空上方可能残留的“添加成功”提示文字
                status_update = ""

            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"❌ 删除知识库文件失败: {e}")

    # ------------------------------------------
    # 3. 统一获取并渲染文档列表
    # ------------------------------------------
    # 无论上面执行了上传还是删除，最后都重新读取一次文件列表进行渲染
    try:
        if hasattr(turbine_system, 'kb_adapter'):
            docs_info = turbine_system.kb_adapter.list_documents()
        else:
            docs_info = turbine_system.list_documents()

        documents = docs_info.get("documents", {})

        if not documents:
            doc_list_ui = fac.AntdEmpty(description="知识库目前为空，尚未添加任何文档")
        else:
            cards = []
            for file_path, meta in documents.items():
                file_name = meta.get("file_name", os.path.basename(file_path))
                doc_type = meta.get("doc_type", "未知类型")
                chunk_count = meta.get("chunk_count", 0)

                encoded_path = base64.b64encode(file_path.encode('utf-8')).decode('utf-8')

                card = fac.AntdCard(
                    title=f"📄 {file_name}",
                    extra=fac.AntdPopconfirm(
                        fac.AntdButton("🗑️ 删除", type="primary", danger=True, size="small"),
                        title=f"确定要彻底删除 {file_name} 吗？",
                        okText="确定删除",
                        okButtonProps={'danger': True},
                        cancelText="取消",
                        id={'type': 'kb-delete-btn', 'index': encoded_path}
                    ),
                    children=[
                        html.Div(f"存储路径: {file_path}",
                                 style={'fontSize': '12px', 'color': '#8c8c8c', 'wordBreak': 'break-all'}),
                        html.Div(f"文件类型: {doc_type} | 拆分片段数: {chunk_count}", style={'marginTop': '5px'})
                    ],
                    style={'marginBottom': '10px', 'backgroundColor': '#fafafa'}
                )
                cards.append(card)

            doc_list_ui = html.Div(cards)

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"获取知识库列表失败: {e}")
        doc_list_ui = fac.AntdAlert(message="加载知识库列表失败，请检查系统后台日志。", description=str(e), type="error")

    # 同时返回上传状态和文档列表组件
    return status_update, doc_list_ui


