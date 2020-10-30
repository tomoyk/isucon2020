from os import getenv, path
import json
import subprocess
from io import StringIO
import csv
import flask
from werkzeug.exceptions import BadRequest, NotFound
import mysql.connector
from sqlalchemy.pool import QueuePool
from humps import camelize

import json
import redis
# r = redis.Redis(host='localhost', port=6379, decode_responses=True, db=0)
r = redis.Redis(unix_socket_path='/var/run/redis/redis-server.sock', decode_responses=True, db=0)

LIMIT = 20
NAZOTTE_LIMIT = 50

chair_search_condition = json.load(open("../fixture/chair_condition.json", "r"))
estate_search_condition = json.load(open("../fixture/estate_condition.json", "r"))

app = flask.Flask(__name__)
import logging
app.logger.setLevel(logging.INFO)

mysql_connection_env = {
    "host": getenv("MYSQL_HOST", "127.0.0.1"),
    "port": getenv("MYSQL_PORT", 3306),
    "user": getenv("MYSQL_USER", "isucon"),
    "password": getenv("MYSQL_PASS", "isucon"),
    "database": getenv("MYSQL_DBNAME", "isuumo"),
}

mysql_connection_env2 = {
    "host": "192.168.0.82",
    "port": 3306,
    "user": "isucon",
    "password": "isucon",
    "database": "isuumo",
}

mysql_connection_env3 = {
    "host": "192.168.0.83",
    "port": 3306,
    "user": "isucon",
    "password": "isucon",
    "database": "isuumo",
}

cnxpool = QueuePool(lambda: mysql.connector.connect(**mysql_connection_env), pool_size=10)

cnxpool_estate = QueuePool(lambda: mysql.connector.connect(**mysql_connection_env2), pool_size=30)
cnxpool_chair = QueuePool(lambda: mysql.connector.connect(**mysql_connection_env3), pool_size=30)

IS_LOCAL_DEV = False
DEBUG_MYLOG = False

def select_all(query, *args, dictionary=True):
    # print(args[0])
    if IS_LOCAL_DEV:
        if DEBUG_MYLOG:
            app.logger.info("other")
        cnx = cnxpool.connect()
    else:
        if ' estate' in query:
            if DEBUG_MYLOG:
                app.logger.info("estate")
            cnx = cnxpool_estate.connect()
        elif ' chair' in query:
            if DEBUG_MYLOG:
                app.logger.info("chair")
            cnx = cnxpool_chair.connect()
        
    try:
        cur = cnx.cursor(dictionary=dictionary)
        cur.execute(query, *args)
        return cur.fetchall()
    finally:
        cnx.close()


def select_row(*args, **kwargs):
    rows = select_all(*args, **kwargs)
    return rows[0] if len(rows) > 0 else None


def select_row2(*args, **kwargs):
    # print(args[0])
    if ' estate' in args[0] and not IS_LOCAL_DEV:
        if DEBUG_MYLOG:
            app.logger.info("estate")
        cnx = cnxpool_estate.connect()
    elif ' chair' in args[0] and not IS_LOCAL_DEV:
        if DEBUG_MYLOG:
            app.logger.info("chair")
        cnx = cnxpool_chair.connect()
    else:
        if DEBUG_MYLOG:
            app.logger.info("other")
        cnx = cnxpool.connect()

    try:
        cur = cnx.cursor(dictionary=True)
        cur.execute(*args, **kwargs)
        row = cur.fetchone()
    finally:
        cnx.close()
    return row if row else None


@app.route("/initialize", methods=["POST"])
def post_initialize():
    r.flushall()

    sql_dir = "../mysql/db"
    sql_files = [
        "0_Schema.sql",
        "1_DummyEstateData.sql",
        "2_DummyChairData.sql",
    ]

    if IS_LOCAL_DEV:
        for sql_file in sql_files:
            command = f"mysql -h {mysql_connection_env['host']} -u {mysql_connection_env['user']} -p{mysql_connection_env['password']} -P {mysql_connection_env['port']} {mysql_connection_env['database']} < {path.join(sql_dir, sql_file)}"
            subprocess.run(["bash", "-c", command])
    else:
        for node in ('192.168.0.83', '192.168.0.82'):
            for sql_file in sql_files:
                '''
                if node == 'comp2' and sql_file == '1_DummyEstateData.sql':
                    continue
                elif node == 'comp3' and sql_file == '2_DummyChairData.sql':
                    continue
                '''
                command = f"mysql -h {node} -u isucon -pisucon -P 3306 isuumo < {path.join(sql_dir, sql_file)}"
                subprocess.run(["bash", "-c", command])

    return {"language": "python"}


@app.route("/api/estate/low_priced", methods=["GET"])
def get_estate_low_priced():
    rows = r.get('estate_low_priced')
    if rows is None:
        rows = select_all("SELECT * FROM estate ORDER BY rent, id LIMIT %s", (LIMIT,))
        # app.logger.info("UnHit EstateLowPriced")
        r.set('estate_low_priced', json.dumps(rows))
    else:
        # app.logger.info("Hit EstateLowPriced")
        rows = json.loads(rows)
    # rows = camelize(select_all("SELECT * FROM estate ORDER BY rent, id LIMIT %s", (LIMIT,)))

    return {"estates": camelize(rows)}


@app.route("/api/chair/low_priced", methods=["GET"])
def get_chair_low_priced():
    rows = r.get('chair_low_priced')
    if rows is None:
        rows = select_all("SELECT * FROM chair WHERE stock > 0 ORDER BY price, id LIMIT %s", (LIMIT,))
        # app.logger.info("UnHit ChairLowPriced")
        r.set('chair_low_priced', json.dumps(rows))
    else:
        # app.logger.info("Hit ChairLowPriced")
        rows = json.loads(rows)
    # rows = select_all("SELECT * FROM chair WHERE stock > 0 ORDER BY price, id LIMIT %s", (LIMIT,))

    return {"chairs": camelize(rows)}


@app.route("/api/chair/search", methods=["GET"])
def get_chair_search():
    args = flask.request.args

    conditions = []
    params = []

    if args.get("priceRangeId"):
        for _range in chair_search_condition["price"]["ranges"]:
            if _range["id"] == int(args.get("priceRangeId")):
                price = _range
                break
        else:
            raise BadRequest("priceRangeID invalid")
        if price["min"] != -1:
            conditions.append("price >= %s")
            params.append(price["min"])
        if price["max"] != -1:
            conditions.append("price < %s")
            params.append(price["max"])

    if args.get("heightRangeId"):
        for _range in chair_search_condition["height"]["ranges"]:
            if _range["id"] == int(args.get("heightRangeId")):
                height = _range
                break
        else:
            raise BadRequest("heightRangeId invalid")
        if height["min"] != -1:
            conditions.append("height >= %s")
            params.append(height["min"])
        if height["max"] != -1:
            conditions.append("height < %s")
            params.append(height["max"])

    if args.get("widthRangeId"):
        for _range in chair_search_condition["width"]["ranges"]:
            if _range["id"] == int(args.get("widthRangeId")):
                width = _range
                break
        else:
            raise BadRequest("widthRangeId invalid")
        if width["min"] != -1:
            conditions.append("width >= %s")
            params.append(width["min"])
        if width["max"] != -1:
            conditions.append("width < %s")
            params.append(width["max"])

    if args.get("depthRangeId"):
        for _range in chair_search_condition["depth"]["ranges"]:
            if _range["id"] == int(args.get("depthRangeId")):
                depth = _range
                break
        else:
            raise BadRequest("depthRangeId invalid")
        if depth["min"] != -1:
            conditions.append("depth >= %s")
            params.append(depth["min"])
        if depth["max"] != -1:
            conditions.append("depth < %s")
            params.append(depth["max"])

    if args.get("kind"):
        conditions.append("kind = %s")
        params.append(args.get("kind"))

    if args.get("color"):
        conditions.append("color = %s")
        params.append(args.get("color"))

    if args.get("features"):
        for feature_confition in args.get("features").split(","):
            conditions.append("features LIKE CONCAT('%', %s, '%')")
            params.append(feature_confition)

    if len(conditions) == 0:
        raise BadRequest("Search condition not found")

    conditions.append("stock > 0")

    try:
        page = int(args.get("page"))
    except (TypeError, ValueError):
        raise BadRequest("Invalid format page parameter")

    try:
        per_page = int(args.get("perPage"))
    except (TypeError, ValueError):
        raise BadRequest("Invalid format perPage parameter")

    search_condition = " AND ".join(conditions)

    query = f"SELECT COUNT(id) as count FROM chair WHERE {search_condition}"
    count = select_row(query, params)["count"]

    query = f"SELECT * FROM chair WHERE {search_condition} ORDER BY popularity DESC, id LIMIT %s OFFSET %s"
    chairs = select_all(query, params + [per_page, per_page * page])

    return {"count": count, "chairs": camelize(chairs)}


@app.route("/api/chair/search/condition", methods=["GET"])
def get_chair_search_condition():
    return chair_search_condition


@app.route("/api/chair/<int:chair_id>", methods=["GET"])
def get_chair(chair_id):
    chair = select_row2("SELECT * FROM chair WHERE id = %s", (chair_id,))
    if chair is None or chair["stock"] <= 0:
        raise NotFound()
    return camelize(chair)


@app.route("/api/chair/buy/<int:chair_id>", methods=["POST"])
def post_chair_buy(chair_id):
    if IS_LOCAL_DEV:
        cnx = cnxpool.connect()
    else:
        cnx = cnxpool_chair.connect()

    try:
        cnx.start_transaction()
        cur = cnx.cursor(dictionary=True)
        # cur.execute("SELECT * FROM chair WHERE id = %s AND stock > 0 FOR UPDATE", (chair_id,))
        cur.execute("UPDATE chair SET stock = stock - 1 WHERE id = %s AND stock > 0", (chair_id,))
        if cur.rowcount <= 0:
            raise NotFound()
        cnx.commit()
        return {"ok": True}
    except Exception as e:
        cnx.rollback()
        raise e
    finally:
        cnx.close()


@app.route("/api/estate/search", methods=["GET"])
def get_estate_search():
    args = flask.request.args

    conditions = []
    params = []

    if args.get("doorHeightRangeId"):
        for _range in estate_search_condition["doorHeight"]["ranges"]:
            if _range["id"] == int(args.get("doorHeightRangeId")):
                door_height = _range
                break
        else:
            raise BadRequest("doorHeightRangeId invalid")
        if door_height["min"] != -1:
            conditions.append("%s <= door_height")
            params.append(door_height["min"])
        if door_height["max"] != -1:
            conditions.append("door_height < %s")
            params.append(door_height["max"])

    if args.get("doorWidthRangeId"):
        for _range in estate_search_condition["doorWidth"]["ranges"]:
            if _range["id"] == int(args.get("doorWidthRangeId")):
                door_width = _range
                break
        else:
            raise BadRequest("doorWidthRangeId invalid")
        if door_width["min"] != -1:
            conditions.append("%s <= door_width")
            params.append(door_width["min"])
        if door_width["max"] != -1:
            conditions.append("door_width < %s")
            params.append(door_width["max"])

    if args.get("rentRangeId"):
        for _range in estate_search_condition["rent"]["ranges"]:
            if _range["id"] == int(args.get("rentRangeId")):
                rent = _range
                break
        else:
            raise BadRequest("rentRangeId invalid")
        if rent["min"] != -1:
            conditions.append("%s <= rent")
            params.append(rent["min"])
        if rent["max"] != -1:
            conditions.append("rent < %s")
            params.append(rent["max"])

    if args.get("features"):
        for feature_confition in args.get("features").split(","):
            conditions.append("features LIKE CONCAT('%', %s, '%')")
            params.append(feature_confition)

    if len(conditions) == 0:
        raise BadRequest("Search condition not found")

    try:
        page = int(args.get("page"))
    except (TypeError, ValueError):
        raise BadRequest("Invalid format page parameter")

    try:
        per_page = int(args.get("perPage"))
    except (TypeError, ValueError):
        raise BadRequest("Invalid format perPage parameter")

    search_condition = " AND ".join(conditions)

    query = f"SELECT COUNT(id) as count FROM estate WHERE {search_condition}"
    count = select_row(query, params)["count"]

    query = f"SELECT * FROM estate WHERE {search_condition} ORDER BY popularity_desc, id LIMIT %s OFFSET %s"
    chairs = select_all(query, params + [per_page, per_page * page])
    # app.logger.info(query)

    return {"count": count, "estates": camelize(chairs)}


@app.route("/api/estate/search/condition", methods=["GET"])
def get_estate_search_condition():
    return estate_search_condition


@app.route("/api/estate/req_doc/<int:estate_id>", methods=["POST"])
def post_estate_req_doc(estate_id):
    estate = select_row2("SELECT * FROM estate WHERE id = %s", (estate_id,))
    if estate is None:
        raise NotFound()
    return {"ok": True}


@app.route("/api/estate/nazotte", methods=["POST"])
def post_estate_nazotte():
    if "coordinates" not in flask.request.json:
        raise BadRequest()
    # app.logger.info("MY_DEBUG")
    # app.logger.info(flask.request.json)
    coordinates = flask.request.json["coordinates"]
    if len(coordinates) == 0:
        raise BadRequest()
    longitudes = [c["longitude"] for c in coordinates]
    latitudes = [c["latitude"] for c in coordinates]
    bounding_box = {
        "top_left_corner": {"longitude": min(longitudes), "latitude": min(latitudes)},
        "bottom_right_corner": {"longitude": max(longitudes), "latitude": max(latitudes)},
    }

    if IS_LOCAL_DEV:
        cnx = cnxpool.connect()
    else:
        cnx = cnxpool_estate.connect()

    try:
        polygon_text = (
            f"POLYGON(({','.join(['{} {}'.format(c['latitude'], c['longitude']) for c in coordinates])}))"
        )
        # print(polygon_text)
        cur = cnx.cursor(dictionary=True)
        cur.execute(
            (
                "SELECT * FROM estate"
                " WHERE latitude <= %s AND latitude >= %s AND longitude <= %s AND longitude >= %s"
                " AND ST_Contains(ST_PolygonFromText(%s), POINT(latitude, longitude)) "
                " ORDER BY popularity_desc, id"
                " LIMIT %s"
            ),
            (
                bounding_box["bottom_right_corner"]["latitude"],
                bounding_box["top_left_corner"]["latitude"],
                bounding_box["bottom_right_corner"]["longitude"],
                bounding_box["top_left_corner"]["longitude"],
                polygon_text,
                NAZOTTE_LIMIT,
            ),
        )
        estates = cur.fetchall()
    finally:
        cnx.close()

    results = {"estates": [camelize(estate) for estate in estates]}
    results["count"] = len(results["estates"])
    return results


@app.route("/api/estate/<int:estate_id>", methods=["GET"])
def get_estate(estate_id):
    rows = r.get('estate_item_' + str(estate_id))
    if rows is None:
        rows = select_row2("SELECT * FROM estate WHERE id = %s", (estate_id,))
        if rows is None:
            raise NotFound()
        else:
            r.set('estate_item_' + str(estate_id), json.dumps(rows))
    else:
        rows = json.loads(rows)

    return camelize(rows)


@app.route("/api/recommended_estate/<int:chair_id>", methods=["GET"])
def get_recommended_estate(chair_id):
    chair = select_row2("SELECT * FROM chair WHERE id = %s", (chair_id,))
    if chair is None:
        raise BadRequest(f"Invalid format searchRecommendedEstateWithChair id : {chair_id}")
    w, h, d = chair["width"], chair["height"], chair["depth"]
    '''
    query = (
        "SELECT * FROM estate"
        " WHERE (door_width >= %s AND door_height >= %s)"
        "    OR (door_width >= %s AND door_height >= %s)"
        "    OR (door_width >= %s AND door_height >= %s)"
        "    OR (door_width >= %s AND door_height >= %s)"
        "    OR (door_width >= %s AND door_height >= %s)"
        "    OR (door_width >= %s AND door_height >= %s)"
        " ORDER BY popularity_desc, id"
        " LIMIT %s"
    )
    '''
    query = (
        "SELECT * FROM estate"
        " WHERE (door_width >= %s AND (door_height >= %s OR door_height >= %s))"
        "    OR (door_width >= %s AND (door_height >= %s OR door_height >= %s))"
        "    OR (door_width >= %s AND (door_height >= %s OR door_height >= %s))"
        " ORDER BY popularity_desc, id ASC"
        " LIMIT %s"
    )
    estates = select_all(query, (w, h, d, h, w, d, d, w, h, LIMIT))
    return {"estates": camelize(estates)}


@app.route("/api/chair", methods=["POST"])
def post_chair():
    r.delete('chair_low_priced')

    if "chairs" not in flask.request.files:
        raise BadRequest()
    records = csv.reader(StringIO(flask.request.files["chairs"].read().decode()))
    records = [rec for rec in records]

    if IS_LOCAL_DEV:
        cnx = cnxpool.connect()
    else:
        cnx = cnxpool_chair.connect()

    try:
        cnx.start_transaction()
        cur = cnx.cursor()
        query = "INSERT INTO chair(id, name, description, thumbnail, price, height, width, depth, color, features, kind, popularity, stock) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        cur.executemany(query, records)
        cnx.commit()
        return {"ok": True}, 201
    except Exception as e:
        cnx.rollback()
        raise e
    finally:
        cnx.close()


@app.route("/api/estate", methods=["POST"])
def post_estate():
    r.delete('estate_low_priced')

    if "estates" not in flask.request.files:
        raise BadRequest()
    records = csv.reader(StringIO(flask.request.files["estates"].read().decode()))
    records = [rec for rec in records]

    if IS_LOCAL_DEV:
        cnx = cnxpool.connect()
    else:
        cnx = cnxpool_estate.connect()

    try:
        cnx.start_transaction()
        cur = cnx.cursor()
        query = "INSERT INTO estate(id, name, description, thumbnail, address, latitude, longitude, rent, door_height, door_width, features, popularity) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        cur.executemany(query, records)
        cnx.commit()
        return {"ok": True}, 201
    except Exception as e:
        cnx.rollback()
        raise e
    finally:
        cnx.close()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=getenv("SERVER_PORT", 1323), debug=True, threaded=True)
