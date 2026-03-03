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
                        fac.AntdInput(id='chapter-input', defaultValue="轴流式压缩机", addonBefore="章节/主题"),
                        fac.AntdSelect(id='question-type-select', defaultValue="choice",
                                       options=[{'label': '选择题', 'value': 'choice'},
                                                {'label': '简答题', 'value': 'short_answer'}]),
                        fac.AntdButton("🚀 生成题目", id="generate-btn", type="primary"),
                        html.Div(id='generate-result-container', style={'marginTop': '20px'})
                    ])
                },
                # 可以继续添加作业批改、章节总结的Tab...
            ]
        )

    ])

