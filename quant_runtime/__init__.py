"""Generic quant strategy runtime package.

业务功能: quant_runtime 独立拥有策略元数据、回测配置、行情导入、指标计算和
领域回测结果。
算法要点: appapi 通过 CLI 或 worker 协议调用本包，本包内部再适配具体
回测引擎，目前默认适配 vn.py。
"""
