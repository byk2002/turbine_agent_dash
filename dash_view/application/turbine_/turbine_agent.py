# src/dash_view/application/turbine_/turbine_agent.py
import dash_callback.application.turbine_.turbine_agent_c
from common.utilities.util_menu_access import MenuAccess
from pathlib import Path
from dash import html, dcc
import feffery_antd_components as fac

access_metas = ('透平智能助手-页面',)

title = "智能助手页面"
icon = None
order = 3


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
                                fac.AntdInput(
                                    id='chapter-input',
                                    defaultValue="燃气轮机和汽轮机的热力循环",
                                    value="燃气轮机和汽轮机的热力循环",  # ✅ 新增：确保后端能读到默认值
                                    addonBefore="章节/主题"
                                ),
                                fac.AntdSelect(
                                    id='question-type-select',
                                    defaultValue="choice",
                                    value="choice",  # ✅ 新增
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
                                    value="medium",  # ✅ 新增
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
                                        fac.AntdInputNumber(
                                            id='question-count-input',
                                            defaultValue=5,
                                            value=5,  # ✅ 新增
                                            min=1,
                                            max=20
                                        )
                                    ]
                                ),
                                fac.AntdButton("🚀 生成题目", id="generate-btn", type="primary"),
                            ]
                        ),
                        html.Div(id='generate-result-container', style={'marginTop': '20px'})
                    ])
                },
                {
                    'label': '✅ 作业批改 (支持对比识别)',
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
                                # --- 左右分栏：左边上传学生作业，右边上传参考答案 ---
                                html.Div([
                                    # 左侧：学生作业上传
                                    html.Div([
                                        fac.AntdText("上传学生作业", strong=True,
                                                     style={'marginBottom': '5px', 'display': 'block'}),
                                        dcc.Upload(
                                            id='upload-homework-file',
                                            children=html.Div([
                                                html.Div("📁 点击/拖拽学生作业",
                                                         style={'fontWeight': 'bold', 'fontSize': '14px'}),
                                                html.Div("(PDF/Word/图片)", style={'color': '#888', 'marginTop': '5px',
                                                                                   'fontSize': '12px'})
                                            ]),
                                            style={
                                                'width': '100%', 'height': '80px', 'lineHeight': 'normal',
                                                'borderWidth': '1px', 'borderStyle': 'dashed', 'borderRadius': '8px',
                                                'borderColor': '#1677ff', 'textAlign': 'center', 'paddingTop': '15px',
                                                'backgroundColor': '#e6f4ff', 'cursor': 'pointer'
                                            },
                                            multiple=False
                                        ),
                                        html.Div(id='upload-status-tip',
                                                 style={'color': '#1677ff', 'marginTop': '5px', 'fontSize': '12px',
                                                        'minHeight': '18px'}),
                                    ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top'}),

                                    # 右侧：参考答案上传
                                    html.Div([
                                        fac.AntdText("上传参考答案", strong=True,
                                                     style={'marginBottom': '5px', 'display': 'block'}),
                                        dcc.Upload(
                                            id='upload-standard-answer-file',
                                            children=html.Div([
                                                html.Div("📄 点击/拖拽参考答案",
                                                         style={'fontWeight': 'bold', 'fontSize': '14px'}),
                                                html.Div("(PDF/Word/图片)", style={'color': '#888', 'marginTop': '5px',
                                                                                   'fontSize': '12px'})
                                            ]),
                                            style={
                                                'width': '100%', 'height': '80px', 'lineHeight': 'normal',
                                                'borderWidth': '1px', 'borderStyle': 'dashed', 'borderRadius': '8px',
                                                'borderColor': '#52c41a', 'textAlign': 'center', 'paddingTop': '15px',
                                                'backgroundColor': '#f6ffed', 'cursor': 'pointer'
                                            },
                                            multiple=False
                                        ),
                                        html.Div(id='upload-standard-status-tip',
                                                 style={'color': '#52c41a', 'marginTop': '5px', 'fontSize': '12px',
                                                        'minHeight': '18px'}),
                                    ], style={'width': '48%', 'display': 'inline-block', 'marginLeft': '4%',
                                              'verticalAlign': 'top'}),
                                ], style={'width': '100%', 'marginBottom': '10px'}),
                                # -------------------------

                                fac.AntdInput(
                                    mode='text-area',
                                    id='correction-answer-input',
                                    placeholder="或者手动输入学生的解答内容(选填)...",
                                    autoSize={'minRows': 4, 'maxRows': 10},
                                    style={'width': '100%'}
                                ),
                                fac.AntdButton("🔍 开始对比批改", id="correct-btn", type="primary",
                                               loading_state={'is_loading': False}),
                            ]
                        ),
                        html.Div(id='correction-result-container', style={'marginTop': '20px'})
                    ])
                }
            ]
        )
    ])