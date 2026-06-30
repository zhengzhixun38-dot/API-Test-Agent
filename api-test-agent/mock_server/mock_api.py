"""
模拟业务接口服务 (V2 — 含完整边界校验)
提供 4 个被测试的 REST API：
  POST   /api/user/login     用户登录
  GET    /api/user/info       用户信息
  GET    /api/product/list    商品列表
  POST   /api/order/create    创建订单
"""
import re
import time
from fastapi import FastAPI, Header, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

app = FastAPI(title="Mock Business API", version="2.0.0")

MOCK_TOKEN = "mock-token-2024"
# 扩大有效商品 ID 范围，减少"商品不存在"失败
VALID_PRODUCT_IDS = set(range(1, 101))  # 1-100 都有效


# ═══════════════════════════════════════════════════════════
# 数据模型（含校验）
# ═══════════════════════════════════════════════════════════

class LoginRequest(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str):
        if not v or not v.strip():
            raise ValueError("username 不能为空")
        if len(v) < 3:
            raise ValueError("username 长度不能少于 3 位")
        if len(v) > 20:
            raise ValueError("username 长度不能超过 20 位")
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError("username 只能包含字母、数字和下划线")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str):
        if not v or not v.strip():
            raise ValueError("password 不能为空")
        if len(v) < 6:
            raise ValueError("password 长度不能少于 6 位")
        if len(v) > 20:
            raise ValueError("password 长度不能超过 20 位")
        return v


class OrderRequest(BaseModel):
    product_id: int
    count: int

    @field_validator("product_id")
    @classmethod
    def validate_product_id(cls, v: int):
        if v <= 0:
            raise ValueError("product_id 必须大于 0")
        if v > 99999:
            raise ValueError("product_id 超出范围")
        return v

    @field_validator("count")
    @classmethod
    def validate_count(cls, v: int):
        if v <= 0:
            raise ValueError("count 必须大于 0")
        if v > 999:
            raise ValueError("count 不能超过 999")
        return v


# ═══════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════

def _check_token(authorization: str) -> bool:
    return authorization == f"Bearer {MOCK_TOKEN}"


def _ok(data=None, message="success", status_code=200):
    return JSONResponse(status_code=status_code, content={"code": 0, "message": message, "data": data or {}})


def _fail(code: int, message: str):
    return JSONResponse(status_code=code, content={"code": code, "message": message})


# ═══════════════════════════════════════════════════════════
# 1. 登录接口  POST /api/user/login
# ═══════════════════════════════════════════════════════════

@app.post("/api/user/login")
def user_login(body: LoginRequest):
    """
    用户登录
    规则：
      - username: 3-20 位，仅字母数字下划线
      - password: 6-20 位
      - 任何有效凭据都返回 token（模拟环境）
    """
    # 仅 admin / 123456 可登录成功（模拟真实业务）
    if body.username != "admin" or body.password != "123456":
        return _fail(401, "用户名或密码错误")
    return _ok({"token": MOCK_TOKEN, "username": body.username})


# ═══════════════════════════════════════════════════════════
# 2. 用户信息接口  GET /api/user/info
# ═══════════════════════════════════════════════════════════

@app.get("/api/user/info")
def user_info(authorization: str = Header(default="")):
    """
    获取用户信息
    规则：
      - 必须携带有效 token
      - token 格式: Bearer <token>
    """
    if not authorization:
        return _fail(401, "缺少 Authorization 请求头")
    if not _check_token(authorization):
        return _fail(401, "token 无效或已过期")
    return _ok({
        "id": 1,
        "username": "admin",
        "email": "admin@example.com",
        "role": "admin",
    })


# ═══════════════════════════════════════════════════════════
# 3. 商品列表接口  GET /api/product/list
# ═══════════════════════════════════════════════════════════

@app.get("/api/product/list")
def product_list(
    page: int = Query(default=1, description="页码"),
    page_size: int = Query(default=10, description="每页数量"),
    keyword: str = Query(default="", description="搜索关键词"),
):
    """
    商品列表（分页）
    规则：
      - page: >= 1，超过总页数返回空列表
      - page_size: 1-100
      - keyword: 可选，最长 50 字符
    """
    if page < 1:
        return _fail(400, "page 必须 >= 1")
    if page_size < 1:
        return _fail(400, "page_size 必须 >= 1")
    if page_size > 100:
        return _fail(400, "page_size 最大为 100")
    if len(keyword) > 50:
        return _fail(400, "keyword 长度不能超过 50")

    all_products = [
        {"id": i, "name": f"商品_{i}", "price": round(i * 9.9, 2), "stock": i * 5}
        for i in range(1, 101)
    ]

    # 关键词过滤
    if keyword:
        all_products = [p for p in all_products if keyword in p["name"]]

    total = len(all_products)
    start = (page - 1) * page_size
    end = start + page_size
    page_data = all_products[start:end]

    return _ok({
        "list": page_data,
        "total": total,
        "page": page,
        "page_size": page_size,
    })


# ═══════════════════════════════════════════════════════════
# 4. 创建订单接口  POST /api/order/create
# ═══════════════════════════════════════════════════════════

@app.post("/api/order/create")
def order_create(body: OrderRequest, authorization: str = Header(default="")):
    """
    创建订单
    规则：
      - 必须携带有效 token
      - product_id: >= 1，必须在可售商品列表中
      - count: 1-999
    """
    if not authorization:
        return _fail(401, "缺少 Authorization 请求头")
    if not _check_token(authorization):
        return _fail(401, "token 无效或已过期")
    if body.product_id not in VALID_PRODUCT_IDS:
        return _fail(404, f"商品 {body.product_id} 不存在或已下架")
    if body.count > 999:
        return _fail(400, "count 不能超过 999")

    # Pydantic 已保证 count >= 1, product_id >= 1

    order_id = int(time.time() * 1000) % 100000
    return _ok({
        "order_id": order_id,
        "product_id": body.product_id,
        "count": body.count,
        "total_price": round(body.count * 99.9, 2),
        "status": "created",
    })
