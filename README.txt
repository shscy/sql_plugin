使用场景：
	1. 在使用 sqlalchemy 时，session的管理比较麻烦, 需要在一次请求中保持session的不变。
	2. 使用sqlalchemy的连接池时， mysql重启之后, session是一个过期对象，无法正常使用， 此时需要
	   在不重启web服务的情况下，自动更新链接池。
	3. 在使用uwsgi部署web服务时，通常是多进程+gevent的模式。生成的session没有协程隔离的能力, 同时sqlchemy在
	   对数据库链接之后， 是不能fork的，uwsgi的lazy参数可以做到fork之后create_app避免此问题（曾经在生产换进忘记使用此
	   参数导致诡异bug ^_^).

