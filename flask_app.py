
# A very simple Flask Hello World app for you to get started with...

from flask import Flask, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from ibm_watson import NaturalLanguageUnderstandingV1
from ibm_watson import SpeechToTextV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_watson.natural_language_understanding_v1 import Features, EntitiesOptions, KeywordsOptions , EmotionOptions
from ibm_watson import LanguageTranslatorV3
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_watson.websocket import RecognizeCallback, AudioSource
import os
import json
import time

app = Flask(__name__)
app.config["DEBUG"] = True

SQLALCHEMY_DATABASE_URI = "mysql+mysqlconnector://{username}:{password}@{hostname}/{databasename}".format(
    username="shakibaam",
    password="cloudcomputingHW1",
    hostname="shakibaam.mysql.pythonanywhere-services.com",
    databasename="shakibaam$cc_HW1",
)
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_POOL_RECYCLE"] = 299
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
app_context = app.app_context()


class Movies(db.Model):

    __tablename__ = "Movies"

    MovieID = db.Column(db.Integer, primary_key=True)
    MovieName = db.Column(db.String(255))
    MoviePosterLink = db.Column(db.String(255))
    DirectorName = db.Column(db.String(255))

    def json(self):
        return {
            'MovieID' :self.MovieID,
            'MovieName' : self.MovieName,
            'MoviePosterLink': self.MoviePosterLink,
            'DirectorName' :self. DirectorName,

        }


class Comments(db.Model):

    __tablename__ = "Comments"

    CommentID = db.Column(db.Integer, primary_key=True)
    MovieID = db.Column(db.Integer, db.ForeignKey('Movies.MovieID'))
    UserName = db.Column(db.String(255))
    CommentText = db.Column(db.Text)


    def json(self):
        return {
            'UserName' : self.UserName,
            'CommentText': self.CommentText,
            'MovieID' :self.MovieID,

        }

    @classmethod

    def save_to_db(self):
        db.session.add(self)
        db.session.commit()

class MyRecognizeCallback(RecognizeCallback):
    def __init__(self):
        RecognizeCallback.__init__(self)

    def on_data(self, data):
        print(json.dumps(data, indent=2))

    def on_error(self, error):
        print('Error received: {}'.format(error))

    def on_inactivity_timeout(self, error):
        print('Inactivity timeout: {}'.format(error))


@app.route('/' , methods=["GET"])
def get_movies():
   return {'Movies': list(map(lambda x: x.json(), Movies.query.all()))}

@app.route('/<int:id>' , methods=["GET" , "POST"])
def get_and_post_movie_comments(id):
    if request.method == "GET":

        comments = list(map(lambda x: x.json(), Comments.query.filter_by(MovieID=id).all()))
        translated_comments = []
        lang = request.args.get('lang')
        for comment in comments :
            tr_comment = languageTranslator(comment['CommentText'] , lang)
            translated_comments.append(tr_comment)
        if(len(translated_comments)>0):
            return {'translated_comments' : translated_comments} , 200
        else:
            return 'No comments for this movie' , 200


        return {'Comments': list(map(lambda x: x.json(), Comments.query.filter_by(MovieID=id).all()))}
        # return languageTranslator('hello' , 'en-es')

    elif request.method == "POST" :
        if 'file' not in request.files:
          return 'no filee'
        else:
              try:

                  os.path.exists("/home/shakibaam/mysite/comments/{}".format(id))
              except :
                  os.mkdir("/home/shakibaam/mysite/comments/{}".format(id))

              file = request.files['file']
              file_name = secure_filename(file.filename)
              user_name = str(file_name).split(".")[0]

              destination= "/home/shakibaam/mysite/comments/{}".format(id)
              file.save(destination)
              comment_text = speechToText(destination)
              anger = natrualLanguageUnderstanding(comment_text)


        if(anger == 'OK'):


            try :
                comment = Comments(MovieID = id , UserName = user_name , CommentText =  comment_text)

                db.session.add(comment)
                db.session.commit()
                return "Comment added", 201

            except :
                return "can not add to database , try again" , 201
        else:
            return 'This comment is Angry we are not allowed to add it' , 201


def speechToText(file_destination) :
      # Setup Service
      authenticator = IAMAuthenticator('38ee2N87YSb5j-trSX_uFLU_lMD56QLn84aH0JlHpSs5')
      speech_to_text = SpeechToTextV1(authenticator=authenticator)
      speech_to_text.set_service_url('https://api.us-east.speech-to-text.watson.cloud.ibm.com/instances/7a197e68-03c6-4696-b9e0-0652d46267d5')


      with open(file_destination, 'rb') as audio_file:

            dic = json.loads(
                    json.dumps(
                        speech_to_text.recognize(
                            audio=audio_file,
                            content_type='audio/mp3',
                            model='en-US_NarrowbandModel'
                        ).get_result(), indent=2))


      str = ""

      while bool(dic.get('results')):
         str = dic.get('results').pop().get('alternatives').pop().get('transcript')+str[:]

      return str

def natrualLanguageUnderstanding(comment) :
    authenticator = IAMAuthenticator('QEddzum-bjf9WgvrZSn4UUjXfC-B8SjhUEFw2QztsYdN')
    natural_language_understanding = NaturalLanguageUnderstandingV1(version='2021-03-25',authenticator=authenticator)

    natural_language_understanding.set_service_url('https://api.us-south.natural-language-understanding.watson.cloud.ibm.com/instances/0acc1745-4ca3-4f9e-9cf8-88a65bef9c31')

    response = natural_language_understanding.analyze(text=comment,language='en',features= Features(emotion=EmotionOptions())).get_result()
    anger = response['emotion']['document']['emotion']['anger']


    if(anger>0.5) :
        return "angry"
    else:
        return "OK"


def languageTranslator(comment , lang):

    authenticator = IAMAuthenticator('9FxUVTFy40cRd8FO2-5Yo2Cru4w0ogN0wgkm65Sriq0n')
    language_translator = LanguageTranslatorV3(version='2018-05-01',authenticator=authenticator)
    language_translator.set_service_url('https://api.us-east.language-translator.watson.cloud.ibm.com/instances/1d8b309c-0172-4891-8135-d9e79f29802f')

    res = language_translator.translate(text=comment,model_id='en-es').get_result()
    translated_comment = res["translations"][0]["translation"]

    return translated_comment










