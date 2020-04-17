# Shelter Called API
This codebase provides two basic functions:
1. Supports api calls from Twilio in response to events from Twilio Studio and saves data
2. Support a front-end dashboard to display data and admin features 

Twilio logic that repsonds to users is primarily handled through a Twilio studio "flow" (https://www.twilio.com/studio). Twilio flows can be imported and exported as JSON. The current flow JSON file is part of this repo at `/twilio_studio/studio.flow.json`

The front-end is a seperate app written with Vue that hits this api. 

## Install
Clone repo
```
git clone http://url….git
cd bedcount_backend
```

Set up virtual env and load it
```
python -m venv venv
source venv/bin/activate
```

Install dependencies
```
pip install -r requirements.txt
```

If deploying to app engine, install dependencies in /lib
```
pip install -t lib -r requirements.txt
```

## Environment
The app will expect to find several environmental variables the define behavior, api tokens, and DB connections. When running in production on App Engine these will be defined in `app_env.yaml`. See `app_env_black.yaml` for a list of expected variables. These variables are also needed in development. A nice way to handle this is to place the definitions in a `config.sh` file outside the repro and load them with `source ../path_to_config.sh. 

## Setting up database
The app will expect to have a PostgreSQL database. This can be installed locally, in docker container, or on Google Cloud using 
Cloud SQL Proxy (https://cloud.google.com/sql/docs/mysql/sql-proxy)

The app will expect to find an env named: `SQLALCHEMY_DATABASE_URI` that is a connection string to the database. 

This uses flask migrations to mantain the database. To run the migrations on the DB use:
```
flask db upgrade
```

## Run in Development
Make sure required environmental variables are set and database is running.
```
flask run
```

## Deploy to App Engine
The api is a basic Flask app. It should be possible to deploy anywhere you can run flask, but it has been designed with Google App Engine Standard Environment in mind.
The app requires several environmental variables to be set to inform the system about twilio api keys and various other config options. See `app_env_blank.yaml` for current variables. Create a new file named `app_env.yaml` and define these variable here. The file will be included into `app.yaml` and set the environment on the production server.

To deploy to app engine, set up a project following directions here: https://cloud.google.com/appengine/docs/standard/python3/quickstart
Once the SDK is installed, `cd` into the folder with `app.yaml` and run

```
gcloud app deploy
```
This will create a new instance on app engine, but will not start sending traffic to it. You can log into the Google Console, run the version to make sure it meets requirements and then migrate traffic to it.

## Twilio Setup
The telephone/sms aspects of this app are handled by [Twilio studio](https://www.twilio.com/studio). Studio works by creating flows created as a set of nodes and connections via Twilio's user interface. Certain nodes in the flow will hit this api to save data or validate input. The file `twilio_studio/studio.flow.json` can be used to recreate a working flow on studio. However, the URL for the api calls must be hard-coded in this JSON file. The included file has placeholders for the base_url `<BASE_URL>`. To use this in production, replace strings `<BASE_URL>` with the actual url used in production. Then follow instruction on twilio studio to create a new flow from a JSON document.