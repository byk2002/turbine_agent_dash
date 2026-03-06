# src/dash_view/application/turbine_/turbine_agent.py
# 🔴 这两行绝对不能丢，否则会导致按钮失效或报错！
import dash_callback.application.turbine_.turbine_agent_c  #绑定所有的按钮点击和后台响应（回调函数）
from pathlib import Path
from common.utilities.util_menu_access import MenuAccess
from dash import html, dcc
import feffery_antd_components as fac
# 引入大模型实例，用于读取评分
from common.turbine_core.instance import turbine_system
access_metas = ('透平智能助手-页面',)

title = "智能助手页面"
icon = None
order = 3


def render_content(menu_access: MenuAccess, **kwargs):
    # 1. 使用当前登录的真实用户名作为大模型的 session_id
    session_id = menu_access.user_name

    # 2. 从大模型的持久化存储中读取当前用户的评分与画像
    user_profile = turbine_system.load_profile(session_id)

    # 3. 提取数据并做展示美化
    elo_rating = user_profile.get("elo_rating", 1200)
    skill_level = user_profile.get("skill_level", "beginner")
    weak_points = user_profile.get("weak_points", [])

    # 等级翻译映射
    level_map = {
        "beginner": "🌱 初学者",
        "intermediate": "🚀 进阶者",
        "advanced": "👑 专家"
    }
    level_display = level_map.get(skill_level, skill_level)
    weak_points_str = "，".join(weak_points) if weak_points else "暂无"

    return html.Div([
        # 保存真实的用户 session_id 给回调使用
        dcc.Store(id='turbine-session-store', data={'session_id': session_id}),

        fac.AntdTitle("⚙️ 透平机械原理智能教学助手", level=2, style={'marginBottom': '20px'}),

        # ===== 🌟 用户画像与评分展示面板 (纯手工 Flexbox 完美居中版) =====
        fac.AntdCard(
            title="🧑‍🎓 我的学习档案 (基于大模型动态评估)",
            style={'marginBottom': '20px', 'backgroundColor': '#f8fafd', 'borderRadius': '8px'},
            headStyle={'fontWeight': 'bold'},
            children=[
                # 使用原生 Div 开启 flex 布局，space-around 保证三个元素完美等距且居中
                html.Div(
                    style={
                        'display': 'flex',
                        'justifyContent': 'space-around',
                        'alignItems': 'center',
                        'width': '100%',
                        'padding': '10px 0'
                    },
                    children=[
                        # --- 模块 1：能力值 ---
                        html.Div(
                            style={'textAlign': 'center'},
                            children=[
                                html.Div("当前能力值 (Elo)",
                                         style={'color': '#8c8c8c', 'fontSize': '14px', 'marginBottom': '8px'}),
                                html.Div(elo_rating,
                                         style={'color': '#cf1322', 'fontSize': '28px', 'fontWeight': 'bold'})
                            ]
                        ),

                        # --- 模块 2：等级 ---
                        html.Div(
                            style={'textAlign': 'center'},
                            children=[
                                html.Div("系统评估等级",
                                         style={'color': '#8c8c8c', 'fontSize': '14px', 'marginBottom': '8px'}),
                                html.Div(level_display, style={
                                    'color': '#096dd9',
                                    'fontSize': '26px',
                                    'fontWeight': 'bold',
                                    'whiteSpace': 'nowrap'  # 强制不换行
                                })
                            ]
                        ),

                        # --- 模块 3：薄弱点 ---
                        html.Div(
                            style={'textAlign': 'center'},
                            children=[
                                html.Div("待巩固薄弱点",
                                         style={'color': '#8c8c8c', 'fontSize': '14px', 'marginBottom': '8px'}),
                                html.Div(weak_points_str,
                                         style={'color': '#d48806', 'fontSize': '18px', 'fontWeight': 'bold'})
                            ]
                        )
                    ]
                )
            ]
        ),
        # ============================================

        fac.AntdTabs(
            id='turbine-tabs',
            type='card',  # 改用卡片式 Tabs，视觉更清晰
            items=[
                {
                    'label': '💬 智能问答',
                    'key': 'qa-tab',
                    'children': html.Div([
                        # 1. 聊天记录显示区
                        html.Div(
                            id='chat-history-container',
                            style={
                                'height': '450px',
                                'overflowY': 'auto',
                                'padding': '15px',
                                'backgroundColor': '#ffffff',
                                'border': '1px solid #f0f0f0',
                                'borderRadius': '8px',
                                'marginBottom': '20px'
                            }
                        ),
                        # 2. 独立的输入框包装区 (在这里控制缩短和居中)
                        html.Div(
                            fac.AntdInput(
                                mode='search',
                                id='chat-input',
                                placeholder="请输入关于透平机械的问题，按回车发送...",
                                size="large",
                                # 控制输入框自身的高度和圆角
                                style={'height': '50px', 'fontSize': '16px', 'borderRadius': '8px'}
                            ),
                            # 控制整个输入框居中，并且占据 70% 的宽度
                            style={'width': '70%', 'margin': '0 auto'}
                        )
                    ], style={'padding': '10px'}) # 给整个问答区一点内边距
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
                                    value="燃气轮机和汽轮机的热力循环",
                                    addonBefore="章节/主题"
                                ),
                                fac.AntdSelect(
                                    id='question-type-select',
                                    defaultValue="choice",
                                    value="choice",
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
                                    value="medium",
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
                                            value=5,
                                            min=1,
                                            max=20
                                        )
                                    ]
                                ),
                                fac.AntdButton("🚀 生成题目", id="generate-btn", type="primary"),
                            ]
                        ),
                        html.Div(id='generate-result-container', style={'marginTop': '20px'})
                    ], style={'padding': '10px'})
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
                    ], style={'padding': '10px'})
                }
            ]
        )
    ])
