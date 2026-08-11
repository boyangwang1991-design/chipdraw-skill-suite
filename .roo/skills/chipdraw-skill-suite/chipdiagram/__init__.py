"""芯片研发智能绘图 Skill Suite 核心包。

提供统一的芯片图形语义模型（SSOT）、Schema 校验、专业规则校验、视图选择、
确定性渲染后端编排、结构 QA 与 Manifest 发布能力。

典型使用：
    from chipdiagram import load_and_normalize, validate, select_views, render, publish
"""
from .pipeline import (
    load_and_normalize,
    validate,
    select_views,
    compute_layout,
    render,
    inspect_artifacts,
    publish,
)

__version__ = "1.0.0"
__all__ = [
    "load_and_normalize",
    "validate",
    "select_views",
    "compute_layout",
    "render",
    "inspect_artifacts",
    "publish",
    "__version__",
]
