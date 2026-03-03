# src/dash_view/application/turbine_/turbine_agent.py

from common.utilities.util_menu_access import MenuAccess
from pathlib import Path
import base64
from dash import (
    html, dcc,
    Input, Output, State,
    callback, no_update,
    callback_context
)
import feffery_antd_components as fac
from dash_components import Card

# 【DashGo规范】必须定义权限元数据，以便菜单和权限工厂识别
access_metas = ('透平智能助手-页面',)

title = "智能助手页面"
icon = None
order = 2

def render_content(menu_access: MenuAccess, **kwargs):
    return html.Div([
        # 会话状态存储
        dcc.Store(id='turbine-session-store', data={'session_id': 'default_user_session'}),

        fac.AntdTitle("⚙️ 透平机械原理智能教学助手", level=2),

        fac.AntdTabs(
            id='turbine-tabs',
            items=[
                {
                    'label': '💬 智能问答',
                    'key': 'qa-tab',
                    'children': html.Div([
                        # 聊天记录展示区
                        html.Div(id='chat-history-container', style={'height': '400px', 'overflowY': 'auto'}),
                        # 输入区
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
                        # 使用 AntdSpace 让一行可以整齐排列多个输入控件
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
                                        {'label': '计算题', 'value': 'calculation'} # 新增计算题
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
                                        fac.AntdInputNumber(
                                            id='question-count-input', 
                                            defaultValue=3, 
                                            min=1, 
                                            max=20 # 限制最多一次生成20题
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
                    'label': '✅ 作业批改',
                    'key': 'correction-tab',
                    'children': html.Div([
                        fac.AntdSpace(
                            direction='vertical',
                            style={'width': '100%'},
                            children=[
                                fac.AntdInput(
                                    id='correction-question-input',
                                    addonBefore="原题目",
                                    placeholder="请输入需要批改的原题目内容...",
                                    style={'width': '100%'}
                                ),
                                fac.AntdInput(
                                    mode='text-area',
                                    id='correction-answer-input',
                                    placeholder="请输入学生的解答内容...",
                                    autoSize={'minRows': 4, 'maxRows': 15},
                                    style={'width': '100%'}
                                ),
                                fac.AntdButton("🔍 开始批改", id="correct-btn", type="primary"),
                            ]
                        ),
                        # 批改结果展示区
                        html.Div(id='correction-result-container', style={'marginTop': '20px'})
                    ])
                }
            ]
        )
    ])
