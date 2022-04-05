from flask import Flask
from flask_restx import Resource, Api, reqparse, fields, marshal_with
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
api = Api(app)
db = SQLAlchemy(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'


class PeopleDB(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    age = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f"id:{self.id}, name:{self.name}, age:{self.age}"


people_get_rep = reqparse.RequestParser()
people_get_rep.add_argument("name", type=str)

people_post_rep = reqparse.RequestParser()
people_post_rep.add_argument("name", type=str)
people_post_rep.add_argument("age", type=int)


@api.route("/helloworld/<int:actor_id>")
class HelloWorld(Resource):
    def get(self, actor_id):
        return {"data": ""}

    def post(self):
        pass

    def patch(self):
        pass

    def delete(self):
        pass


resource_field = {
    "id": fields.Integer,
    "name": fields.String,
    "age": fields.Integer
}


# @api.route("/people")
class People(Resource):
    @api.expect(people_get_rep)
    def get(self):
        args = people_get_rep.parse_args()
        return {"data": args['name']}

    @api.expect(people_post_rep)
    # @marshal_with(resource_field)
    def post(self):
        args = people_post_rep.parse_args()
        people_id = 1
        name = args["name"]
        age = args["age"]
        someone = PeopleDB(name=name, age=age)
        db.session.add(someone)
        db.session.commit()
        return {"data": [name, age]}, 200


# @api.route("/people/<int:people_id>")
class People_edit(Resource):
    def delete(self, people_id):
        people_delete = PeopleDB.query.get_or_404(people_id)
        db.session.delete(people_delete)
        db.session.commit()
        return {"id": people_id}, 204


api.add_resource(People, '/people')
api.add_resource(People_edit, '/people/<int:people_id>')

if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)
    pass
