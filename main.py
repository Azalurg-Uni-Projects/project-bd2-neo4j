from flask import Flask, jsonify, request
from neo4j import GraphDatabase
from dotenv import load_dotenv
import os  # provides ways to access the Operating System and allows us to read the environment variables

load_dotenv()

app = Flask(__name__)

uri = os.getenv('URI')
user = os.getenv("USERNAME")
password = os.getenv("PASSWORD")
driver = GraphDatabase.driver(uri, auth=(user, password), database="neo4j")


def get_employees(tx, position=None, sort_by='surname', sort_order='ASC'):
    query = "MATCH (e:Employee) "
    if position:
        query += f"WHERE e.position = '{position}' "
    query += f"RETURN e ORDER BY e.{sort_by} {sort_order}"
    results = tx.run(query).data()
    employees = [
        {'employee': result['e']['name'], 'surname': result['e']['surname'], 'position': result['e']['position']} for
        result in results]
    return employees


@app.route('/employees', methods=['GET'])
def get_employees_route():
    position = request.args.get('position')
    sort_by = request.args.get('sort_by', 'surname')
    sort_order = request.args.get('sort_order', 'ASC')
    with driver.session() as session:
        employees = session.read_transaction(get_employees, position, sort_by, sort_order)

    response = {'employees': employees}
    return jsonify(response)


def add_employee(tx, name, surname, position):
    query = "CREATE (e:Employee {name: $name, surname: $surname, position: $position})"
    tx.run(query, name=name, surname=surname, position=position)


@app.route('/employees', methods=['POST'])
def add_employee_route():
    name = request.json['name']
    surname = request.json['surname']
    position = request.json['position']

    with driver.session() as session:
        session.write_transaction(add_employee, name, surname, position)

    response = {'status': 'success'}
    return jsonify(response)


def update_employee(tx, name, new_name, new_surname, new_position):
    query = "MATCH (e:Employee) WHERE e.name=$name RETURN e"
    result = tx.run(query, name=name).data()

    if not result:
        return None
    else:
        query = "MATCH (e:Employee) WHERE e.name=$name SET e.name=$new_name, e.surname=$new_surname, e.position=$new_position"
        tx.run(query, name=name, new_name=new_name, new_surname=new_surname, new_position=new_position)
        return {'name': new_name, 'surname': new_surname, 'position': new_position}


@app.route('/employees/<string:name>', methods=['PUT'])
def update_employee_route(name):
    new_name = request.json['name']
    new_surname = request.json['surname']
    new_position = request.json['position']

    with driver.session() as session:
        employee = session.write_transaction(update_employee, name, new_name, new_surname, new_position)

    if not employee:
        response = {'message': 'Employee not found'}
        return jsonify(response), 404
    else:
        response = {'status': 'success'}
        return jsonify(response)


def delete_employee(tx, name):
    query = "MATCH (e:Employee) WHERE e.name=$name RETURN e"
    result = tx.run(query, name=name).data()

    if not result:
        return None
    else:
        query = "MATCH (e:Employee) WHERE e.name=$name DETACH DELETE e"
        tx.run(query, name=name)
        return {'name': name}


@app.route('/employees/<string:name>', methods=['DELETE'])
def delete_employee_route(name):
    with driver.session() as session:
        employee = session.write_transaction(delete_employee, name)

    if not employee:
        response = {'message': 'Employee not found'}
        return jsonify(response), 404
    else:
        response = {'status': 'success'}
        return jsonify(response)

if __name__ == '__main__':
    app.run()
