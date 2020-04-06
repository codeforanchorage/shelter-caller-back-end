`$ export FLASK_ENV=development`
`$ flask run`
(On Windows, use `set` instead of `export`.)

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