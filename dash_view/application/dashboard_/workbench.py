# 导入菜单访问控制模块，用于管理用户对菜单的访问权限
from common.utilities.util_menu_access import MenuAccess

# 导入随机数生成模块，用于生成示例数据
import random

# 导入图表组件库，用于创建各种图表
import feffery_antd_charts as fact

# 导入图表组件库，用于支持双轴图组件
from feffery_antd_charts import AntdDualAxes

# 导入Ant Design风格的UI组件库
import feffery_antd_components as fac

# 导入工具组件库，提供额外的功能组件
import feffery_utils_components as fuc

# 导入样式工具，用于简化样式定义
from feffery_dash_utils.style_utils import style

# 从自定义组件模块导入Card卡片组件
from dash_components import Card

# 再次导入fac（虽然重复，但保持原代码结构）
import feffery_antd_components as fac

# 导入日志工具，用于记录日志
from common.utilities.util_logger import Log

# 导入国际化翻译函数，用于多语言支持
from i18n import t__dashboard


# 导入 math 模块
import math

# 定义二级菜单的显示标题
title = '工作台'

# 定义菜单图标（这里为None表示不使用图标）
icon = None

# 定义菜单在导航中的显示顺序（数字越小越靠前）
order = 1

# 创建当前模块的日志记录器实例
logger = Log.get_logger(__name__)

# 定义访问权限元数据，控制用户对该页面的访问权限
access_metas = ('工作台-页面',)


def chart_block(title, chart):
    """示例自定义组件，返回仪表盘区块
    参数:
        title: 区块标题文本
        chart: 图表组件对象
    返回:
        包含标题和图表的Flex布局组件
    """
    
    # 返回一个垂直排列的Flex布局，包含标题和图表
    return fac.AntdFlex(
        [
            # 标题文本组件，带有左侧边框和左内边距样式
            fac.AntdText(
                title,  # 标题文本
                # 应用自定义样式：左侧3px蓝色边框，左侧8px内边距，字体大小15px
                style=style(borderLeft='3px solid #1890ff', paddingLeft=8, fontSize=15),
            ),
            # 图表组件
            chart,
        ],
        vertical=True,  # 设置为垂直方向排列
        gap=8,  # 子元素之间的间距为8px
        # 容器样式：高度设置为100%减去20px，留出边距空间
        style=style(height='calc(100% - 20px)'),
    )


def render_content(menu_access: MenuAccess, **kwargs):
    """渲染工作台页面内容的主要函数
    参数:
        menu_access: MenuAccess对象，包含用户信息和访问权限
        **kwargs: 其他可选参数
    返回:
        包含整个页面布局的Space组件
    """
    
    # 返回垂直方向的Space布局容器
    return fac.AntdSpace(
        [
            # 用户信息卡片
            Card(
                # 卡片内部的水平排列Space
                fac.AntdSpace(
                    [
                        # 用户头像组件
                        fac.AntdAvatar(
                            id='workbench-avatar',  # 组件ID
                            mode='image',  # 显示模式为图片
                            # 头像图片路径，使用用户名构建
                            src=f'/avatar/{menu_access.user_info.user_name}',
                            # 头像alt文本，显示用户全名
                            alt=menu_access.user_info.user_full_name,
                            size=70,  # 头像尺寸70px
                            style={'marginRight': '20px'},  # 右侧外边距20px
                        ),
                        # 问候文本，使用国际化翻译
                        fac.AntdText(t__dashboard('你好，')),
                        # 显示用户全名，带有ID用于可能的JS交互
                        fac.AntdText(menu_access.user_info.user_full_name, id='workbench-user-full-name'),
                    ]
                )
            ),
            
            # 网格布局容器，用于排列所有图表区块
            fuc.FefferyGrid(
                [
                    # 网格项1：双Y轴折线图示例
                    fuc.FefferyGridItem(
                        chart_block(
                            title='双Y轴折线图示例',
                            chart=fact.AntdDualAxes(
                                # 提供两组数据，分别对应左右两个Y轴
                                data=[
                                    # 第一组数据（对应左Y轴）
                                    [
                                        {
                                            'date': f'2020-{i:02d}',
                                            'value1': random.randint(50, 100),
                                        }
                                        for i in range(1, 50)
                                    ],
                                    # 第二组数据（对应右Y轴）
                                    [
                                        {
                                            'date': f'2020-{i:02d}',
                                            'value2': math.sin(random.randint(i-1,i+2)/4) + random.uniform(0.05, 0.2),
                                        }
                                        for i in range(1, 50)
                                    ]
                                ],
                                xField='date',
                                yField=['value1', 'value2'],
                                # 配置几何图形
                                geometryOptions=[
                                    {
                                        'geometry': 'line',
                                        'color': '#1890ff',
                                    },
                                    {
                                        'geometry': 'line',
                                        'color': '#ff4d4f',
                                    }
                                ],
                                # 配置Y轴，设置双Y轴
                                yAxis={
                                    'value1': {
                                        'position': 'left',
                                        # 设置左Y轴标签颜色与第一条折线相同
                                        'label': {
                                            'style': {
                                                'fill': '#1890ff',  # 蓝色，与第一条折线颜色一致
                                            }
                                        },
                                        # 可选：设置轴线颜色
                                        'line': {
                                            'style': {
                                                'stroke': '#1890ff',  # 蓝色轴线
                                                'opacity': 0.5,       # 半透明
                                            }
                                        }
                                    },
                                    'value2': {
                                        'position': 'right',
                                        # 新增：设置右Y轴标签颜色与第二条折线相同
                                        'label': {
                                            'style': {
                                                'fill': '#ff4d4f',  # 红色，与第二条折线颜色一致
                                            }
                                        },
                                        # 可选：设置轴线颜色
                                        'line': {
                                            'style': {
                                                'stroke': '#ff4d4f',  # 红色轴线
                                                'opacity': 0.5,       # 半透明
                                            }
                                        }
                                    }
                                },
                                # 保留滑块控件
                                slider={},
                                # 设置图表高度
                                height=400,
                                # 添加内边距，确保图表内容不被裁剪
                                padding='auto',
                            ),
                        ),
                        key='双Y轴折线图示例',
                        # 关键修改：在网格项级别设置最小高度
                        style={'minHeight': '450px', 'height': '100%'},
                    ),
                    
                    # 网格项2：面积图示例
                    fuc.FefferyGridItem(
                        chart_block(
                            title='面积图示例',
                            chart=fact.AntdArea(
                                data=[
                                    {
                                        'date': f'2020-0{i}',
                                        'y': random.randint(50, 100),
                                    }
                                    for i in range(1, 10)
                                ],
                                xField='date',
                                yField='y',
                                # 面积填充样式：使用线性渐变
                                areaStyle={'fill': 'l(270) 0:#ffffff 0.5:#7ec2f3 1:#1890ff'},
                            ),
                        ),
                        key='面积图示例',
                    ),
                    
                    # 网格项3：分组柱状图示例
                    fuc.FefferyGridItem(
                        chart_block(
                            title='柱状图示例',
                            chart=fact.AntdColumn(
                                data=[
                                    {
                                        'date': f'2020-0{i}',
                                        'y': random.randint(0, 100),
                                        'type': f'item{j}',  # 分组字段
                                    }
                                    for i in range(1, 10)  # 9个月
                                    for j in range(1, 4)   # 3种类型
                                ],
                                xField='date',
                                yField='y',
                                seriesField='type',  # 按类型分组
                                isGroup=True,  # 启用分组显示
                            ),
                        ),
                        key='柱状图示例',
                    ),
                    
                    # 网格项4：条形图示例
                    fuc.FefferyGridItem(
                        chart_block(
                            title='条形图示例',
                            chart=fact.AntdBar(
                                data=[
                                    {
                                        'year': '1951 年',
                                        'value': 38,
                                    },
                                    {
                                        'year': '1952 年',
                                        'value': 52,
                                    },
                                    {
                                        'year': '1956 年',
                                        'value': 61,
                                    },
                                    {
                                        'year': '1957 年',
                                        'value': 145,
                                    },
                                    {
                                        'year': '1958 年',
                                        'value': 48,
                                    },
                                ],
                                xField='value',  # 条形图X轴是数值
                                yField='year',   # 条形图Y轴是分类
                                seriesField='year',  # 按年份设置颜色
                                legend={
                                    'position': 'top-left',  # 图例位置在左上角
                                },
                            ),
                        ),
                        key='条形图示例',
                    ),
                    
                    # 网格项5：饼图示例
                    fuc.FefferyGridItem(
                        chart_block(
                            title='饼图示例',
                            chart=fact.AntdPie(
                                data=[
                                    {
                                        'type': f'item{i}',  # 分类名称
                                        'x': random.randint(50, 100),  # 数值
                                    }
                                    for i in range(1, 6)  # 生成5个分类
                                ],
                                colorField='type',  # 按类型字段分配颜色
                                angleField='x',     # 角度字段
                                radius=0.9,        # 饼图半径比例
                            ),
                        ),
                        key='饼图示例',
                    ),
                    
                    # 网格项6：双轴图示例（组合折线图和柱状图）
                    fuc.FefferyGridItem(
                        chart_block(
                            title='双轴图示例',
                            chart=fact.AntdDualAxes(
                                data=[
                                    # 左轴数据：折线图数据
                                    [
                                        {
                                            'date': f'2020-0{i}',
                                            'y1': random.randint(50, 100),
                                        }
                                        for i in range(1, 10)
                                    ],
                                    # 右轴数据：柱状图数据
                                    [
                                        {
                                            'date': f'2020-0{i}',
                                            'y2': random.randint(100, 1000),
                                        }
                                        for i in range(1, 10)
                                    ],
                                ],
                                xField='date',
                                yField=['y1', 'y2'],  # 双Y轴字段
                                # 几何图形配置：第一个为折线，第二个为柱状
                                geometryOptions=[
                                    {'geometry': 'line',
                                     'color': '#1890ff',  # 设置折线颜色为蓝色
                                    },
                                    {'geometry': 'column',
                                     'color': '#ff4d4f',  # 设置柱状图颜色为红色
                                    },
                                ],
                                # 配置Y轴，设置标尺数字颜色与对应图形一致
                                yAxis={
                                    'y1': {
                                        'position': 'left',
                                        # 设置左Y轴标签颜色与折线相同
                                        'label': {
                                            'style': {
                                                'fill': '#1890ff',  # 设置蓝色，与折线颜色一致
                                            }
                                        },
                                        # 可选：设置轴线颜色
                                        'line': {
                                            'style': {
                                                'stroke': '#1890ff',  # 蓝色轴线
                                                'opacity': 0.5,       # 半透明
                                            }
                                        }
                                    },
                                    'y2': {
                                        'position': 'right',
                                        # 设置右Y轴标签颜色与柱状图相同
                                        'label': {
                                            'style': {
                                                'fill': '#ff4d4f',  # 设置红色，与柱状图颜色一致
                                            }
                                        },
                                        # 可选：设置轴线颜色
                                        'line': {
                                            'style': {
                                                'stroke': '#ff4d4f',  # 红色轴线
                                                'opacity': 0.5,       # 半透明
                                            }
                                        }
                                    }
                                },
                            ),
                        ),
                        key='双轴图示例',
                    ),
                    
                    # 网格项7：迷你面积图示例
                    fuc.FefferyGridItem(
                        chart_block(
                            title='迷你面积图示例',
                            chart=fact.AntdTinyArea(
                                data=[random.randint(50, 100) for _ in range(20)],  # 20个随机数据点
                                height=60,    # 固定高度
                                smooth=True,  # 启用平滑曲线
                            ),
                        ),
                        key='迷你面积图示例',
                    ),
                    
                    # 网格项8：进度条图示例
                    fuc.FefferyGridItem(
                        chart_block(
                            title='进度条图示例',
                            chart=fact.AntdProgress(
                                percent=0.7,        # 进度百分比70%
                                barWidthRatio=0.2,  # 进度条宽度比例
                            ),
                        ),
                        key='进度条图示例',
                    ),
                    
                    # 网格项9：进度环图示例
                    fuc.FefferyGridItem(
                        chart_block(
                            title='进度环图示例',
                            chart=fact.AntdRingProgress(
                                percent=0.6,        # 进度百分比60%
                                color=['#F4664A', '#E8EDF3'],  # 进度色和背景色
                                innerRadius=0.85,   # 内半径比例
                                radius=0.98,        # 外半径比例
                                # 统计信息配置
                                statistic={
                                    'title': {
                                        'style': {
                                            'color': '#363636',
                                            'fontSize': '12px',
                                            'lineHeight': '14px',
                                        },
                                        'formatter': {'func': "() => '进度'"},  # 显示"进度"文字
                                    },
                                },
                            ),
                        ),
                        key='进度环图示例',
                    ),
                ],
                # 关键修改：更新网格布局配置，修正键名并避免重叠
                layouts=[
                    # 双Y轴折线图示例 - 使用新键名，增加高度
                    dict(i='双Y轴折线图示例', x=0, y=0, w=1, h=3),  # h=3增加高度，避免被遮挡
                    
                    # 面积图示例
                    dict(i='面积图示例', x=1, y=0, w=1, h=2),
                    
                    # 柱状图示例
                    dict(i='柱状图示例', x=2, y=0, w=1, h=2),
                    
                    # 条形图示例 - 调整位置到双Y轴折线图下方
                    dict(i='条形图示例', x=0, y=3, w=1, h=2),  # y=3确保在双Y轴折线图下方
                    
                    # 饼图示例
                    dict(i='饼图示例', x=1, y=2, w=1, h=2),
                    
                    # 双轴图示例
                    dict(i='双轴图示例', x=2, y=2, w=1, h=2),
                    
                    # 迷你面积图示例 - 调整位置
                    dict(i='迷你面积图示例', x=0, y=5, w=1, h=1),
                    
                    # 进度条图示例 - 调整位置
                    dict(i='进度条图示例', x=1, y=4, w=1, h=1),
                    
                    # 进度环图示例 - 调整位置
                    dict(i='进度环图示例', x=2, y=4, w=1, h=2),
                ],
                cols=3,        # 网格列数：3列
                rowHeight=150, # 每行高度：150px
                placeholderBorderRadius='5px',  # 占位符圆角
                margin=[12, 12],  # 网格项外边距：[垂直，水平]
                # 修正：使用style参数而不是containerStyle
                style={'minHeight': '1200px', 'width': '100%'},
            ),
        ],
        direction='vertical',  # Space组件垂直排列
        style={'width': '100%'},  # 占据100%宽度
    )