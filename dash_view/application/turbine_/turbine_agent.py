# src/dash_view/application/turbine_/turbine_agent.py

from common.utilities.util_menu_access import MenuAccess
from pathlib import Path
from dash import html, dcc
import feffery_antd_components as fac

access_metas = ('透平智能助手-页面',)

title = "智能助手页面"
icon = None
order = 2

def render_content(menu_access: MenuAccess, **kwargs):
    return html.Div([
        dcc.Store(id='turbine-session-store', data={'session_id': 'default_user_session'}),

        fac.AntdTitle("⚙️ 透平机械原理智能教学助手", level=2),

        fac.AntdTabs(
            id='turbine-tabs',
            items=[
                {
                    'label': '💬 智能问答',
                    'key': 'qa-tab',
                    'children': html.Div([
                        html.Div(id='chat-history-container', style={'height': '400px', 'overflowY': 'auto'}),
                        fac.AntdInput(
                            mode='search',
                            id='chat-input',
                            placeholder="请输入关于透平机械的问题...",
                            size="large"
                        )
                    ])
                },
                {
                    'label': '📝 生成练习题',
                    'key': 'generate-tab',
                    'children': html.Div([
                        fac.AntdSpace(
                            direction='horizontal',
                            wrap=True,
                            style={'marginBottom': '15px'},
                            children=[
                                fac.AntdInput(id='chapter-input', defaultValue="轴流式压缩机", addonBefore="章节/主题"),
                                fac.AntdSelect(
                                    id='question-type-select', 
                                    defaultValue="choice",
                                    options=[
                                        {'label': '选择题', 'value': 'choice'},
                                        {'label': '简答题', 'value': 'short_answer'},
                                        {'label': '计算题', 'value': 'calculation'}
                                    ],
                                    style={'width': '120px'}
                                ),
                                fac.AntdSelect(
                                    id='difficulty-select', 
                                    defaultValue="medium",
                                    options=[
                                        {'label': '简单', 'value': 'easy'},
                                        {'label': '中等', 'value': 'medium'},
                                        {'label': '困难', 'value': 'hard'}
                                    ],
                                    style={'width': '100px'}
                                ),
                                fac.AntdSpace(
                                    children=[
                                        fac.AntdText("题目数量:"),
                                        fac.AntdInputNumber(id='question-count-input', defaultValue=3, min=1, max=20)
                                    ]
                                ),
                                fac.AntdButton("🚀 生成题目", id="generate-btn", type="primary"),
                            ]
                        ),
                        html.Div(id='generate-result-container', style={'marginTop': '20px'})
                    ])
                },
                {
                    'label': '✅ 作业批改 (支持视觉识别)',
                    'key': 'correction-tab',
                    'children': html.Div([
                        fac.AntdSpace(
                            direction='vertical',
                            style={'width': '100%'},
                            children=[
                                fac.AntdInput(
                                    id='correction-question-input',
                                    addonBefore="原题目",
                                    placeholder="请输入需要批改的原题目内容(选填)...",
                                    style={'width': '100%'}
                                ),
                                # --- 新增的文件上传区 ---
                                dcc.Upload(
                                    id='upload-homework-file',
                                    children=html.Div([
                                        html.Div("📁 点击或拖拽文件到此处", style={'fontWeight': 'bold', 'fontSize': '16px'}),
                                        html.Div("支持上传 PDF, Word 或 图片文件供大模型识别", style={'color': '#888', 'marginTop': '5px'})
                                    ]),
                                    style={
                                        'width': '100%', 'height': '100px', 'lineHeight': 'normal',
                                        'borderWidth': '1px', 'borderStyle': 'dashed', 'borderRadius': '8px',
                                        'borderColor': '#1677ff', 'textAlign': 'center', 'paddingTop': '25px',
                                        'backgroundColor': '#fafafa', 'cursor': 'pointer', 'marginBottom': '10px'
                                    },
                                    multiple=False
                                ),
                                html.Div(id='upload-status-tip', style={'color': '#52c41a', 'marginBottom': '10px'}), # 用于显示已上传文件名
                                # -------------------------
                                fac.AntdInput(
                                    mode='text-area',
                                    id='correction-answer-input',
                                    placeholder="或者手动输入学生的解答内容...",
                                    autoSize={'minRows': 4, 'maxRows': 10},
                                    style={'width': '100%'}
                                ),
                                fac.AntdButton("🔍 开始智能批改", id="correct-btn", type="primary", loading_state={'is_loading': False}),
                            ]
                        ),
                        html.Div(id='correction-result-container', style={'marginTop': '20px'})
                    ])
                }
            ]
        )
    ])
