# **\*\*\*\***\*\*\***\*\*\*\***

# Intro

Hey, welcome to the Roseware project! It is a pretty big project, so I will try to explain it as best I can.
If you dont care what I have to say and just want to start the project, go to the next section titled "Starting The Project".
If you have any questions, feel free to ask me. I will try to keep this readme up to date as best I can. If you get setup or get stuck there is more usage doccumentation at https://www.rosewareintegrations.com/.
Also, I'm sure there are revisions to be made in the docs, so if you see anything that needs to be changed, feel free to let me know.

There are 3 environments right now. Dev, staging and production. The staging and production branches are setup to require a pr in gitub before merging. I did this because those branches are already being used
for live environments, the dev branch is not. So if you are working on a feature, here is the workflow I would suggest:

- Create a new branch off of dev
- Do your work
- Push your branch to github
- Create a pr to merge your branch into dev
- then once dev is in a stable state we can make a pr into staging

Staging is live on a seperate domain with sandbox accounts. Here are the domains for each environment:

Backend:

- Dev: http://localhost:8000/admin/
- Staging: https://www.api-staging.rosewareintegrations.com/admin/
- Production: https://www.api.rosewareintegrations.com/admin/

Frontend:

- Dev: http://127.0.0.1:5173/
- Staging: https://staging.rosewareintegrations.com/
- Production: https://www.rosewareintegrations.com/

Oce you get everything up and running here is the experience I'm going for. You open the website, explore it, and then create an account. Easy. When you finish making you account you
are dropped onto your dashboard. (pause: as far as frontend ui, this is as far as I have gotten. The backend functionality is mostly in place, and the fronend authentication system works.
But there are still a few big bugs and potential imporvements to be made. un-pause): On the dashboard there are 3 selections. Webpages, Integrations and Marketing.

Webpages: This is where they request that we make them a website, or register their website into our services. I'm not really sure how this part will look yet.

Marketing: This will basically just be two Ayrshare buttons that connect to the users social media. The marketing system is mostly working already.
If you look at `apps/marketing_manager/models` you will see the models for the marketing system. It all runs on celery task running a cron schedule with celery beat. (There is a celery section)
It can generate social media posts and blogs generated with OpenAI and keeps to a planned montly schedule with generated topics ahgead of time. It still needs to make use of midjourny.

Integrations: This is where the user will connect their accounts to our system. I am working on transitioning the api away from api keys and environment variables in favor of oauth.
This way we can store our users access and refresh tokens (probably in aws secrets manager) and use them to make api calls. This allows us to make api calls on behalf of our users.

- All integrations are trigged on an objects save method. Look at `apps/acounts/models.py` and checkout the class Customer. Notice the save method just calles a celery task.
  The triggers a long loop of tasks and webhooks that keep the users data synced with the third party api. This is where it kind of gets confusing...

... To be continued.

# **\*\*\*\***\*\*\***\*\*\*\***

# Starting The Project

- First you need to open the projects vertual environment and install the dependencies

  1: Open a terminal navigated to the root of this project
  2: Run the command `pipenv shell && pipenv install`
  3: Before starting the server you should follow the rest of the steps...

# **\*\*\*\***\*\*\***\*\*\*\***

# Set environment variables

- There are some environment variables you need to set up

  1: Create a new file called .env and put it in the roseware root directory
  2: At the bottom of the read me you will find the environment variables
  3: Just copy and past them in your .env and fill in all the fields as you go

  - For the api keys, you can either setup your own accounts and use those,
    or hit up greyland and he can give you the keys for the test accounts.

# **\*\*\*\***\*\*\***\*\*\*\***

# Set up a database

- You need a PostgreSQL database to run this project.
- If you don't have one you can download it here -> `https://www.postgresql.org/download/`
- You could also get "PG Admin 4" or some other database GUI to help.

  1: You need to create a database, and a postgres user in the GUI, or in the comand line
  2: And save the details to use in these environment variables:

  - DB_NAME=
  - DB_USER=
  - DB_PASSWORD=

# **\*\*\*\***\*\*\***\*\*\*\***

# Create a super user

- Next you need to create a admin user for yourself

  1: In your normal django terminal, navigated to the root of this app,
  Run the command `pipenv shell && python manage.py createsuperuser`
  2: Follow the text propts in the terminal.
  3: Use something you will remember easily.

# **\*\*\*\***\*\*\***\*\*\*\***

# Start the server

- Start the app

  1: Run the command `pipenv shell && python manage.py runserver`
  2: In your browser go to `http://localhost:8000/admin/`
  3: Login with your super user credentials from the last step.

- Next you just need to set up the front end.

# **\*\*\*\***\*\*\***\*\*\*\***

# CELERY SETUP

- Side note: You dont really need to start celery to use the app. Regular authentication
  and general CRUD opreations will work fine. But if you want to test or work on any of the
  syncing features you will need to start celery. Same goes for the webhooks and scheduled tasks.

1: RabbitMQ Setup

- You need to install rabbitmq on your machine. Set up will be different for different os, it might be kind of a pain.
  - See here for help with rabbitmq => https://docs.celeryq.dev/en/v4.2.1/getting-started/brokers/rabbitmq.html
  - But no matter what you need rabbitmq setup on your machine. https://www.rabbitmq.com/
  - And set `RABBITMQ_USERNAME=` & `RABBITMQ_PASSWORD=` environment variables
  - Thats it! Now just turn it all on!

2: Turn It On

- Open up a terminal on the side somethere, you'll need at least 3.
- In the first terminal, start your rabbitmq server => `sudo rabbitmq-server`
- Open another new server and navigate to the root of this app,
- From there run => `pipenv shell` then, `celery -A roseware worker`.
- Repeat the previous step but run this command => `pipenv shell` then, `celery -A roseware worker -B`. You only need to run this if you are testing the scheduled tasks.
  And now your done, and ready to starty using Celery!

# **\*\*\*\***\*\*\***\*\*\*\***

# SETUP WEBHOOKS

- You need to set up webhooks for all of the platform syncing to work.
- To test the webhooks you can use ngrok. run `./ngrok http 8000` the copy the url and put in in the .env variable called `BACKEND_URL=url`
- Once that is set, you can run the commands `python manage.py create_pipedrive_webhooks` and `python manage.py create_stripe_webhooks`.
- After that all the platforms should be synced and ready to go.

# **\*\*\*\***\*\*\***\*\*\*\***

# NOTES

- You will need to add the Toggles to the admin panel to be able to use the app.

# **\*\*\*\***\*\*\***\*\*\*\***

# EVNIRONMENT VARIABLES

- Copy and paste the rest of the file into your .env and fill out the empty variables.

# Database

DB_NAME=you-db-name
DB_USER=your-db-user
DB_PASSWORD=your-db-password
DB_HOST=127.0.0.1
DB_PORT=5432
BACKEND_URL=your-ngrok-tunnel
HTTP_AUTH_USER=your-superuser-username
HTTP_AUTH_PASSWORD=your-superuser-password
SECRET_KEY=ask-greyland
PORT=8000
WEBHOOK_SECRET_TOKEN=ask-greyland
DJANGO_ENV=development

# OpenAI

OPENAI_API_KEY=

# Celery

RABBITMQ_USERNAME=your-celery-username
RABBITMQ_PASSWORD=your-celery-password

# PIPEDRIVE

PIPEDRIVE_USER_ID=
PIPEDRIVE_API_KEY=
PIPEDRIVE_DOMAIN=
PIPEDRIVE_PERSON_STRIPE_URL_KEY=
PIPEDRIVE_PRODUCT_STRIPE_URL_KEY=
PIPEDRIVE_DEAL_STRIPE_URL_KEY=
PIPEDRIVE_DEAL_TYPE_FIELD=
PIPEDRIVE_DEAL_SUBSCRIPTION_SELECTOR=
PIPEDRIVE_DEAL_PAYOUT_SELECTOR=
PIPEDRIVE_CLIENT_ID=
PIPEDRIVE_CLIENT_SECRET=

# Stripe

STRIPE_PRIVATE=

# Ayrshare - PERSONAL ACCOUNT

AYRSHARE_API_KEY=

# AWS

AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_S3_BUCKET_NAME=

# Monday - You can ignore this for now

MONDAY_API_URL=
MONDAY_API_KEY=
MONDAY_LEADS_BOARD_ID=
MONDAY_ClientS_BOARD_ID=
MONDAY_PACKAGES_BOARD_ID=

# **\*\*\*\***\*\*\***\*\*\*\***

_DOCKER_

To install the api, run: `docker compose up --build`. 

You will need to get into PGAdmin and connect the db. Log in with the `PGADMIN_MAIL` and `PGADMIN_PW` you specified in your .env file.
The server needs to be registered to the `DB_HOST` you specified in your .env file, and a database needs to be created with your `DB_NAME`.

Then login into Rabbitmq's management dashboard with username and password `guest`.
You will need to create a new user with the username and password you specified in your .env file and an admin tag.
Create a new virtual host with the name `roseware` and grant your user access to it. 

To get into the shell of a container and execute commands run: `docker exec -it {container name} {command}`
For example, to create a superuser, run: `docker exec -it django python manage.py createsuperuser`

# **\*\*\*\***\*\*\***\*\*\*\***