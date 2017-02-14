# -*- coding: utf-8 -*-

from .flask_sqlalchemy_plugin import DataBaseSessionProxy, SessionManager


def __init_database():
    mysql_mongo_session_manager_obj = DataBaseSessionProxy(SessionManager)
    def _get_current_session_manager():
        nonlocal mysql_mongo_session_manager_obj
        return mysql_mongo_session_manager_obj

    return _get_current_session_manager


current_session_manager = DataBaseSessionProxy(__init_database())
