import json
import numpy as np
from flask import Flask, request
from flask_restx import Resource, Api, reqparse, fields
from flask_sqlalchemy import SQLAlchemy
import requests
from datetime import datetime, timedelta

app = Flask(__name__)
api = Api(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class ActorDB(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    last_update = db.Column(db.DateTime, default=datetime.now(), nullable=False)
    name = db.Column(db.String(70), nullable=False)
    gender = db.Column(db.String(70), nullable=True)
    country = db.Column(db.String(70), nullable=True)
    birthday = db.Column(db.DateTime, nullable=True)
    deathday = db.Column(db.DateTime, nullable=True)
    show = db.Column(db.Text, nullable=True)

    # def __repr__(self):
    #     return f"self name:{self.name}"


actor_post_parser = reqparse.RequestParser()
actor_post_parser.add_argument("name", type=str)

actor_get_list_parser = reqparse.RequestParser()
actor_get_list_parser.add_argument("order", type=str, default=["+id"], action="split")
actor_get_list_parser.add_argument("page", type=int, default=1)
actor_get_list_parser.add_argument("size", type=int, default=10)
actor_get_list_parser.add_argument("filter", type=str, default=["id", "name"], action="split")

actor_get_stat_parser = reqparse.RequestParser()
actor_get_stat_parser.add_argument("format", type=str)
actor_get_stat_parser.add_argument("by", type=str, action="split")


@api.route("/actors")
class People(Resource):

    @api.expect(actor_get_list_parser)
    def get(self):
        parse = actor_get_list_parser.parse_args()
        _order = parse["order"]
        _page = parse["page"]
        _size = parse["size"]
        _filter = parse["filter"]
        print(_filter)
        actor_from_DB = ActorDB.query.filter(_filter[0])

        return {"actors": actor_from_DB.id}

    @api.expect(actor_post_parser)
    def post(self):
        args = actor_post_parser.parse_args()
        name = args["name"]
        people_info_url = "https://api.tvmaze.com/search/people?q=" + name
        tvmaze_response = json.loads(requests.get(people_info_url).text)[0]
        tvmaze_response_people_info = tvmaze_response["person"]
        tvmaze_id = tvmaze_response_people_info["id"]
        tvmaze_name = tvmaze_response_people_info["name"]
        tvmaze_country = tvmaze_response_people_info["country"]["name"]
        tvmaze_gender = tvmaze_response_people_info["gender"]
        if tvmaze_response_people_info["birthday"]:
            tvmaze_birthday = datetime.strptime(tvmaze_response_people_info["birthday"], "%Y-%m-%d")
        else:
            tvmaze_birthday = None
        if tvmaze_response_people_info["deathday"]:
            tvmaze_deathday = datetime.strptime(tvmaze_response_people_info["deathday"], "%Y-%m-%d")
        else:
            tvmaze_deathday = None

        tvmaze_shows = []
        castcredits_url = "https://api.tvmaze.com/people/" + str(tvmaze_id) + "/castcredits"
        tvmaze_castcredits_response = json.loads(requests.get(castcredits_url).text)
        for item in tvmaze_castcredits_response:
            show_url = item["_links"]["show"]["href"]
            show_url_response = json.loads(requests.get(show_url).text)
            tvmaze_shows.append(show_url_response["name"])

        actor = ActorDB(name=tvmaze_name, country=tvmaze_country, gender=tvmaze_gender, birthday=tvmaze_birthday,
                        deathday=tvmaze_deathday, show=str(tvmaze_shows))
        print(actor)
        db.session.add(actor)
        db.session.commit()

        actor_from_DB = ActorDB.query.filter_by(name=tvmaze_name).first()
        return {"id": actor_from_DB.id,
                "last-update": datetime.strftime(actor_from_DB.last_update, "%Y-%m-%d-%H:%M:%S"),
                "_links": {
                    "self": {
                        "href": "http://127.0.0.1:5000/actors/" + str(actor_from_DB.id)
                    }
                }
                }


@api.route("/actors/<int:actor_id>")
class PeopleOperate(Resource):
    def get(self, actor_id):
        actor_from_DB = ActorDB.query.get_or_404(actor_id)
        actor_previous = ActorDB.query.filter(ActorDB.id < actor_id).order_by(ActorDB.id.desc()).first()
        actor_next = ActorDB.query.filter(ActorDB.id > actor_id).order_by(ActorDB.id.asc()).first()

        _json = {"id": actor_from_DB.id,
                 "last-update": datetime.strftime(actor_from_DB.last_update, "%Y-%m-%d-%H:%M:%S"),
                 "birthday": datetime.strftime(actor_from_DB.birthday, "%d-%m-%Y"),
                 "name": actor_from_DB.name,
                 "country": actor_from_DB.country,
                 "shows": actor_from_DB.show,
                 "_links": {
                     "self": {
                         "href": "http://127.0.0.1:5000/actors/" + str(actor_from_DB.id)
                     }

                 }
                 }
        if actor_previous:
            previous_id = str(actor_previous.id)
            _json["_links"]["previous"] = {"href": "http://127.0.0.1:5000/actors/" + previous_id}
        if actor_next:
            next_id = str(actor_next.id)
            _json["_links"]["next"] = {"href": "http://127.0.0.1:5000/actors/" + next_id}

        return _json

    def delete(self, actor_id):
        actor_from_DB = ActorDB.query.get_or_404(actor_id)
        db.session.delete(actor_from_DB)
        db.session.commit()

        return {"message": "The actor with id " + str(actor_id) + " was removed from the database!",
                "id": actor_id
                }

    def patch(self, actor_id):
        actor_from_DB = ActorDB.query.get_or_404(actor_id)
        body = request.get_json()
        for attribute, value in body.items():
            if attribute == "birthday" or attribute == "deathday":
                if value:
                    value = datetime.strptime(value, "%d-%m-%Y")
            if getattr(actor_from_DB, attribute) != value:
                setattr(actor_from_DB, attribute, value)
        db.session.commit()
        # no birthday or deathday
        updated_actor_from_DB = ActorDB.query.get_or_404(actor_id)
        return {
            "id": updated_actor_from_DB.id,
            "last-update": updated_actor_from_DB.last_update,
            "_links": {
                "self": {
                    "href": "http://127.0.0.1:5000/actors/" + str(updated_actor_from_DB.id)
                }
            }
        }


@api.route("/actors/statistics")
class PeopleStatistics(Resource):
    @api.expect(actor_get_stat_parser)
    def get(self):
        args = actor_get_stat_parser.parse_args()
        _format = args["format"]
        by = args["by"]
        total = ActorDB.query.count()
        total_update = ActorDB.query.filter(
            ActorDB.last_update > (datetime.now() - timedelta(hours=24))).count()
        return_json = {
            "total": total,
            "total-updated": total_update
        }

        if "country" in by:
            group_by_country = db.session.query(ActorDB.country, db.func.count(ActorDB.id).label("total")).group_by(
                ActorDB.country).all()
            # country_list = []
            # for data in group_by_country:
            #     country_list = data["country"]
            country_list = [data["country"] for data in group_by_country]
            print(country_list)
            count_list = np.array([data["total"] for data in group_by_country])
            count_list = list(count_list / count_list.sum())
            return_json["by-country"] = {country_list[i]: count_list[i] for i in range(len(count_list))}

        if "birthday" in by:
            all_birthday = db.session.query(ActorDB.birthday).all()
            age_list = [int(datetime.now().strftime("%Y")) - int(data.birthday.strftime("%Y")) for data in all_birthday
                        if data.birthday]
            age_list = np.array(age_list)
            return_json["by-birthday"] = {"max-age": int(age_list.max()), "min - age": int(age_list.min())}

        if "gender" in by:
            group_by_gender = db.session.query(ActorDB.gender, db.func.count(ActorDB.id).label("total")).group_by(
                ActorDB.gender).all()
            gender_list = [data["gender"] for data in group_by_gender]
            count_list = np.array([data["total"] for data in group_by_gender])
            count_list = list(count_list / count_list.sum())
            return_json["by-gender"] = {gender_list[i]: count_list[i] for i in range(len(count_list))}

        # if "life_status" in by:
        #     group_by_gender = db.session.query(ActorDB.deathday, db.func.count(ActorDB.id).label("total")).group_by(
        #         ActorDB.deathday).all()
        #     gender_list = [data["deathday"] for data in group_by_gender]
        #     count_list = np.array([data["total"] for data in group_by_gender])
        #     count_list = list(count_list / count_list.sum())
        #     return_json["by-life_status"] = {gender_list[i]: count_list[i] for i in range(len(count_list))}
        return return_json


@app.before_first_request
def create_tables():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True)
    pass
