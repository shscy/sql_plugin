# -*- coding: utf-8 -*-

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError, InterfaceError
from weakref import WeakValueDictionary
from flask import current_app
from flask.views import MethodView
import datetime


try:
    from greenlet import getcurrent as get_ident
except ImportError:
    try:
        from thread import get_ident
    except ImportError:
        from _thread import get_ident


class DataBaseSessionProxy(object):
    __slots__ = ('__local', '__name__')
    def __init__(self, local, name=None):
        object.__setattr__(self, '_DataBaseSessionProxy__local', local)
        if name is None:
            name = local.__name__
        object.__setattr__(self, '__name__', name)

    def _get_current_object(self):
        return self.__local()

    def __setitem__(self, key, value):
        self._get_current_object()[key] = value

    def __delitem__(self, key):
        del self._get_current_object()[key]

    __getattr__ = lambda x, n: getattr(x._get_current_object(), n)
    __setattr__ = lambda x, n, v: setattr(x._get_current_object(), n, v)


class SingleInsatance(type):
    def __init__(self, *args, **kwargs):
        self.__instance = None

    def __call__(self, *args, **kwargs):
        if self.__instance is None:
            self.__instance = super(SingleInsatance, self).__call__(*args, **kwargs)
            return self.__instance
        else:
            return self.__instance


class cached_priporty(property):

    def __init__(self, func, name=None, get_dent=get_ident):
        self.func = func
        self.name = name or func.__name__
        self.__storange__ = {}

    def __get__(self, obj, obj_type=None):
        if obj is None:
            return self
        thread_flag = get_ident()
        value = self.__storange__.get(get_ident(), None)
        if value is None:
            value = self.func(obj)
            self.__storange__[thread_flag] = value
        if obj.debug is True:
            print("all_store cached data, self.__storange: ", self.__storange__)
        return value

    def __set__(self, obj, value):
        self.__storange__[get_ident()] = value

    def __delete__(self, obj):
        try:
            del self.__storange__[get_ident()]
        except Exception:
            pass


class SessionChain(object):
    """
    对代理对象进行链式调用， 如果最后的值不是可调用的得到的将是一个代理值,
    为了得到最后的值， 需要调用 get_current_obj
    """
    __slots__ = ("__obj", '__index')

    def __init__(self, obj, times_retry=5):
        object.__setattr__(self, "_SessionProxy__obj", obj)
        object.__setattr__(self, "_SessionProxy__index", times_retry)

    def __getattr__(self, item):
        return SessionChain(getattr(self.__obj, item, None))

    def __call__(self, *args, **kwargs):
        index = 0
        while index < self.__index:
            try:
                return self.__obj(*args, **kwargs)
            except (OperationalError, InterfaceError) as e:
                print("retry to connect")
                index += 1
                current_session_manager.retry_connect()
            except Exception as e:
                index += 1
                raise e

    @property
    def get_current_obj(self):
        return self.__obj


class SessionManager(metaclass=SingleInsatance):
    connect_url = "mysql+mysqlconnector://{user}:{password}@{host}:{port}/{db}"
    def __init__(self, app=None):
        self.init = False
        if app is not None:
            self.init_app(app)

    def init_app(self, flask_app):
        self.user = flask_app.config['MYSQL_USER']
        self.password = flask_app.config['MYSQL_PASSWORD']
        self.host = flask_app.config['MYSQL_HOST'] or 'localhost'
        self.db = flask_app.config['MYSQL_DB']
        self.port = flask_app.config['MYSQL_PORT'] or "3306"
        self.max_overflow  = flask_app.config['MYSQL_MAX_OVERFLOW'] or 2
        self.pool_size = flask_app.config['MYSQL_POOL_SIZE'] or 5
        self.__engine = None
        self.__dbsession = None
        self.debug = flask_app.config['DEBUG']
        self.init = True

    def __connect(self):
        if self.init is False:
            raise RuntimeError("you has not init sessionmanager object")

        self.__engine = create_engine(self.connect_url.format(
            user=self.user, password=self.password, host=self.host, port=self.port, db=self.db),
            max_overflow=self.max_overflow, pool_size=self.pool_size)
        self.__dbsession = sessionmaker(bind=self.__engine)

    @cached_priporty
    def session(self):
        if self.__dbsession is None:
            self.__connect()
        return self.__dbsession()

    def remove_session(self):
        try:
            self.session.close()
            del self.session
        except Exception as e:
            if self.debug is True:
                print("\nremove session error: ", str(e))

    @cached_priporty
    def sql_session(self):
        if self.__dbsession is None:
            self.__connect()
        return self.__engine.connect()

    def remove_sql_session(self):
        try:
            self.sql_session.close()
            del self.sql_session
        except Exception as e:
            if self.debug is True:
                print("\nremove sql_session error: ", str(e))

    def retry_connect(self):
        import time, logging
        index = 1
        while index < 10:
            try:
                self.__dbsession.close_all()
                self.__engine.dispose()
                self.__connect()
            except Exception as e:
                logging.error("[time|%s]mysql connect error" %(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                time.sleep(0.1)
                index +=1
            else:
                break

class View(MethodView):
    def dispatch_request(self, *args, **kwargs):
        try:
            return super().dispatch_request(*args, **kwargs)
        except Exception as e:
            current_session_manager.remove_session()
            current_session_manager.remove_sql_session()
            raise e

