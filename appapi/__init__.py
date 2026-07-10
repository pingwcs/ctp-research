"""FastAPI service for futures market data.

业务功能: appapi 包负责 HTTP 接口、请求/响应 schema、行情读取和回测运行时编排。
算法要点: 算法实现不放在本包内，回测策略和指标计算由 quant_runtime 统一拥有。
"""
