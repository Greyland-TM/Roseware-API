from .models import DailyContent, MarketingSchedule, WeeklyTopic
from dateutil.relativedelta import relativedelta
from datetime import datetime, date, timedelta
from dateutil.relativedelta import SU  # for getting sunday of the week
from dateutil.rrule import rrule, WEEKLY
import textwrap
import openai
import json
import os


def create_customer_monthly_schedule(customer):
    """
    This function should create a MarketingSchedule for
    a given customer using the OpenAI API
    """
    try:
        # Initialize openai and setup an empty marketing schedule object
        print('Setting up monthly schedule topic...')
        openai.api_key = os.environ.get("OPENAI_API_KEY")
        model = "gpt-4"
        token_limit=150

        # Set up the propt with custom details
        organization_field = "software development"
        organization_name = "Roseware Integrations"
        organization_country = "United States"
        organization_state = "Oregon"
        organization_city = "Portland"
        company_details = f"a {organization_field} company, called {organization_name}, from {organization_city} {organization_state}, {organization_country}"
        topics = MarketingSchedule.objects.filter(customer=customer).values_list('topic', flat=True)
        topics_list = list(topics)
        previous_topics = f"These are the topics that have already been used, make sure your topics are all unique: {', '.join(topics_list)}"
        restrictions_list = [
            "The title and topic should no have more than 100 characters in each (less is preferred, short and sweet), This is the most important rule",
            "Your response should only have a json object with a title and a topic field, this is the second most important rule.",
            "Do not make up any events, organizations, festivals, people or places that you were not explicitly told about",
            "Do not state that the organization or company will be present at any events unless it is stated in the events",
        ]
        restrictions = f"Make sure to follow these specific rules very carefully for your response: {', '.join(restrictions_list)}"
        intention = "selling website and business integration tools on https://www.rosewareintegrations.com/"
        system_message = restrictions
        user_message = ' '.join(textwrap.dedent(f"""
            Create a fun and interesting title and topic for a one month social media marketing schedule.
            The topic and title should be creative and unique. Use any holidays, seasons, local celebrations,
            or other things of this nature for helping to pick a topic. {company_details}. {previous_topics}. The date is {datetime.now()},
            and the marketing intention is {intention}.
        """).split())

        # Try and set the topic and title 3 times. Do this incase gpt gives an unexpected response
        for _ in range(3):  
            try:
                response = response = openai.ChatCompletion.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": user_message}
                    ],
                    max_tokens=token_limit,  # Increase the max_tokens to allow the model to generate a more complete response
                    temperature=1,  # Lower temperature makes the output more focused and deterministic
                )

                # Parse the response into the new fields
                response_content = response['choices'][0]['message']['content']
                parsed_content = json.loads(response_content)
                monthly_topic = parsed_content["topic"]
                monthly_title = parsed_content["title"]

                # Get current date and first day of next month
                current_date = datetime.now().date()
                first_day_of_current_month = current_date.replace(day=1)
                first_day_of_next_month = (first_day_of_current_month + relativedelta(months=+1))

                # Check if there is a marketing schedule for this month
                current_monthly_schedule = MarketingSchedule.objects.filter(
                    customer=customer,
                    start_date=first_day_of_current_month
                ).first()

                if current_monthly_schedule:
                    # If a schedule exists for the current month, check for the next month
                    next_monthly_schedule = MarketingSchedule.objects.filter(
                        customer=customer,
                        start_date=first_day_of_next_month
                    ).first()

                    if next_monthly_schedule:
                        # If a schedule also exists for the next month, return a message
                        return {"was_created": False, "message": "You already have a schedule for next month."}
                    else:
                        # Create the new marketing schedule for next month
                        new_marketing_schedule = MarketingSchedule(
                            topic=monthly_topic,
                            title=monthly_title,
                            customer=customer,
                            start_date=first_day_of_next_month
                        )
                else:
                    # If there is no schedule for the current month, create one
                    new_marketing_schedule = MarketingSchedule(
                        topic=monthly_topic,
                        title=monthly_title,
                        customer=customer,
                        start_date=first_day_of_current_month
                    )

                new_marketing_schedule.save()
                return {"was_created": True, "schedule": new_marketing_schedule}
            except Exception as error:
                print(f'Error in create_customer_monthly_schedule: {error}')
                return {"was_created": False, "message": error}

    except Exception as error:
        print(f"Error in create_customer_monthly_schedule surface: {error}")
        return {"was_created": False, "message": error}

def create_schedules_weekly_topics(schedule):
    # Initialize openai and setup an empty marketing schedule object
    openai.api_key = os.environ.get("OPENAI_API_KEY")
    model = "gpt-4"
    token_limit = 150
    total_weeks_for_prompt = 0
    current_week_for_prompt = 0

    # get the start and end of the month
    month = schedule.start_date
    start_date = month.replace(day=1)
    last_day = (start_date + relativedelta(months=+1, days=-1)).day
    end_date = month.replace(day=last_day)

    # get all of the weeks in the month, considering Sunday as the start of the week
    weeks = list(rrule(WEEKLY, dtstart=start_date, until=end_date, byweekday=SU))
    total_weeks_for_prompt = len(weeks)

    # include the end date if it doesn't fall on a Sunday
    if weeks[-1].date() != end_date:
        weeks.append(end_date)

    # get current date and iterate over weeks and create WeeklyTopic objects only for current and future weeks
    today = date.today()
    current_week_start = today - timedelta(days=today.weekday() + 1) if today.weekday() != 6 else today
    for i in range(len(weeks) - 1):
        current_week_for_prompt = i
        
        # if week_start_date is in the past, continue to next iteration
        week_start_date = weeks[i]
        if week_start_date.date() < current_week_start:
            continue
        
        # Set up the propt with custom details
        organization_field = "software development"
        organization_name = "Roseware Integrations"
        organization_country = "United States"
        organization_state = "Oregon"
        organization_city = "Portland"
        company_details = f"a {organization_field} company, called {organization_name}, from {organization_city} {organization_state}, {organization_country}"
        restrictions_list = [
            "The title and topic should no have more than 100 characters in each (less is preferred, short and sweet), This is the most important rule",
            "Your response should only have a json object with a title and a topic field, this is the second most important rule.",
            "Do not make up any events, organizations, festivals, people or places that you were not explicitly told about",
            "Do not state that the organization or company will be present at any events unless it is stated in the events",
        ]
        restrictions = f"Make sure to follow these specific rules very carefully for your response: {', '.join(restrictions_list)}"
        intention = "selling website and business integration tools on https://www.rosewareintegrations.com/"
        topics_list = WeeklyTopic.objects.filter(schedule=schedule).order_by('week_start_date')
        previous_topics_list = [f'{topic.week_start_date}: {topic.title}' for topic in topics_list]
        previous_topics_str = ', '.join(previous_topics_list)
        previous_topics = f"This is for week #{current_week_for_prompt} of {total_weeks_for_prompt} total weeks for this month. The previous topic and titles in order are: {previous_topics_str}"
        system_message = restrictions
        user_message = ' '.join(textwrap.dedent(f"""
            Create a topic and title for one week of social media marketing in a monthly marketing schedule. The topic and title you create should fit
            into the shedules title ({schedule.title}) and topic ({schedule.topic}), it needs to be cohesive and thought out. {previous_topics}.
            The topic and title should be creative and unique. Use any holidays, seasons, local celebrations,
            or other things of this nature for helping to pick a topic. {company_details}. The date is {datetime.now()},
            and the marketing intention is {intention}.
        """).split())

        # Try the request 3 times
        print('Creating new weekly topic...')
        for _ in range(3):
            try:
                response = response = openai.ChatCompletion.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": user_message}
                    ],
                    max_tokens=token_limit,  # Increase the max_tokens to allow the model to generate a more complete response
                    temperature=1,  # Lower temperature makes the output more focused and deterministic
                )

                # Parse the response into the new fields
                response_content = response['choices'][0]['message']['content']
                parsed_content = json.loads(response_content)
                weekly_topic = parsed_content["topic"]
                weekly_title = parsed_content["title"]

                # here you can do the logic of creating WeeklyTopic,
                # for example if the title and topic are generated by GPT
                weekly_topic = WeeklyTopic(
                    schedule=schedule,
                    week_start_date=week_start_date,
                    topic=weekly_topic,
                    title=weekly_title
                )
                weekly_topic.save()
                break

            except Exception as error:
                continue

    return {"was_created": True}

def create_schedules_daily_content(schedule):
    # get the weeks first
    weekly_topics = WeeklyTopic.objects.filter(schedule=schedule).order_by('week_start_date')
    
    return {"was_created": True}
