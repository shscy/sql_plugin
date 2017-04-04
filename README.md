# purpose

* session的请求隔离， 即每一次请求中session对象都是不同的
* 同一次请求中不会产生两个session对象
* session的连接池断开问题，如果Mysql进行了重启，web服务如果不重启，那么session一直无效（简直就是噩梦）
