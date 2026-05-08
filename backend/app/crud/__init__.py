"""CRUD 数据库操作层

目标：抽象数据库操作，后期换数据库只需改此层
"""
from app.crud.base import CRUDBase
from app.crud.user import CRUDUser
from app.crud.strategy import CRUDStrategy, CRUDStrategyTemplate
from app.crud.trade import CRUDTrade
from app.crud.robot import CRUDRobot, CRUDRobotTrade
from app.crud.user_api import CRUDUserAPIConfig
from app.crud.announcement import CRUDAnnouncement

# 单例实例
crud_user = CRUDUser()
crud_strategy = CRUDStrategy()
crud_strategy_template = CRUDStrategyTemplate()
crud_trade = CRUDTrade()
crud_robot = CRUDRobot()
crud_robot_trade = CRUDRobotTrade()
crud_user_api_config = CRUDUserAPIConfig()
crud_announcement = CRUDAnnouncement()
