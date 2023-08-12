import json
import os
import textwrap
from datetime import date, datetime, timedelta

import openai
from dateutil.relativedelta import SU  # for getting sunday of the week
from dateutil.relativedelta import relativedelta
from dateutil.rrule import WEEKLY, rrule
from pytz import timezone
from .models import DailyContent, Day, MarketingSchedule, WeeklyTopic, SocialPost
from roseware.utils import make_logger

logger = make_logger(__name__, stream=True)


def create_monthly_marketing_schedule(customer):

    # Create the base schedule
    schedule = create_customer_monthly_schedule(customer)
    if not schedule["was_created"]:
        logger.error("Failed to create the schedule. Stop command here")
        return
    schedule = schedule['schedule']

    # Create the weekly topics
    for attempt in range(3):
        weeks = create_schedules_weekly_topics(schedule)
        if weeks['was_created']:
            break
        else:
            logger.error(f"There was an issue generating the topics on attempt {attempt + 1}. Trying again now.")
            schedule.delete()
            return False

    # Create the daily contents
    for attempt in range(3):
        contents = create_schedules_daily_content(schedule)
        if contents['was_created']:
            break
        else:
            schedule.delete()
            logger.error(f"There was an issue generating the topics on attempt {attempt + 1}. Trying again now.")
            return False

    return schedule

def create_customer_monthly_schedule(customer):
    """
    This function should create a MarketingSchedule for
    a given customer using the OpenAI API
    """
    try:
        # Initialize openai and setup an empty marketing schedule object
        logger.info('Setting up monthly schedule topic...')
        openai.api_key = os.environ.get("OPENAI_API_KEY")
        model = "gpt-4"
        token_limit = 150

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
            "The title and topic should no have more than 100 characters in each (less is preferred), This is the most important rule",
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
                response = openai.ChatCompletion.create(
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
                logger.error(f'Error in create_customer_monthly_schedule: {error}')
                return {"was_created": False, "message": error}

    except Exception as error:
        logger.error(f"Error in create_customer_monthly_schedule surface: {error}")
        return {"was_created": False, "message": error}

def create_schedules_weekly_topics(schedule):
    """ This function should create a WeeklyTopic for a given MarketingSchedule using the OpenAI API """

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
    for index in range(len(weeks) - 1):
        current_week_for_prompt = index

        # if week_start_date is in the past, continue to next iteration
        week_start_date = weeks[index]
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
        logger.info('Creating new weekly topic...')
        for _ in range(3):
            try:
                response = openai.ChatCompletion.create(
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
                    title=weekly_title,
                    index=index
                )
                weekly_topic.save()
                break

            except Exception as error:
                logger.error(error)
                continue

    return {"was_created": True}

def create_schedules_daily_content(schedule):
    """ This function should create the DailyContents for a given MarketingSchedule using the OpenAI API """

    # Initialize openai and setup an empty marketing schedule object
    openai.api_key = os.environ.get("OPENAI_API_KEY")
    model = "gpt-4"
    token_limit = 150
    total_weeks_for_prompt = 0

    # get the weeks first
    weekly_topics = WeeklyTopic.objects.filter(schedule=schedule).order_by('index')
    customer = weekly_topics.first().schedule.customer
    selected_days = Day.objects.filter(customer=customer)
    current_week_for_prompt = 0
    day_count = 0
    total_weeks_for_prompt = weekly_topics.count()

    if selected_days.count() == 0:
        return {"was_created": False, "message": "No days were selected for this customer"}

    for week in weekly_topics:
        day_count = 0
        current_week_for_prompt = week.index
        for day in selected_days:

            # if day is in the past, continue to next iteration
            pacific = timezone('US/Pacific')
            current_time_pacific = datetime.now(pacific).date()
            if week.week_start_date + timedelta(days=day.index) < current_time_pacific:
                logger.info(f'Skipping day {day.index} because it is in the past')
                day_count += 1
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
            previous_topics_list = [f'{topic.title}' for topic in weekly_topics]
            previous_topics_str = ', '.join(previous_topics_list)
            previous_topics = ' '.join(textwrap.dedent(f"""
                This is for week #{current_week_for_prompt} of {total_weeks_for_prompt} total weeks for this month.
                The previous topic and titles in order are: {previous_topics_str}
            """).split())

            previous_day_topics_list = DailyContent.objects.filter(weekly_topic=week).order_by('index').values_list('title', flat=True)
            previous_topics_str = ', '.join(previous_day_topics_list)
            previous__day_topics = ' '.join(textwrap.dedent(f"""
                This is for {day.name}, and day #{day_count} of {selected_days.count()} total days for this week.
                The previous topic and titles in order are: {previous_topics_str}
            """).split())
            system_message = restrictions
            user_message = ' '.join(textwrap.dedent(f"""
                Create a topic and title for one day of social media marketing in a monthly marketing schedule. The topic and
                title you create should fit into the overall shedules title ({schedule.title}) and topic ({schedule.topic}), it needs
                to be cohesive and thought out. {previous_topics}. {previous__day_topics}. The topic and title should be
                creative and unique. Use any holidays, seasons, local celebrations, or other things of this nature for helping
                to pick a topic. {company_details}. The date is {datetime.now()}, and the marketing intention is {intention}.
            """).split())

            for _ in range(3):
                try:
                    response = openai.ChatCompletion.create(
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
                    daily_topic = parsed_content["topic"]
                    daily_title = parsed_content["title"]
   
                    new_daily_content = DailyContent(
                        weekly_topic=week,
                        daily_topic=daily_topic,
                        title=daily_title,
                        content_type='social_media',
                        scheduled_date=week.week_start_date + timedelta(days=day.index),
                        index=day.index
                    )
                    new_daily_content.save()
                    day_count += 1
                    logger.info('Scheduled daily content...')
                    break
                except Exception as error:
                    logger.error(error)
                    continue
    return {"was_created": True}

def create_social_post(content, platforms):
    logger.info('creating social post...')

    # Initialize openai and setup an empty marketing schedule object
    daily_content = content
    openai.api_key = os.environ.get("OPENAI_API_KEY")
    model = "gpt-4"
    token_limit = 150

    # Set up the propt with custom details
    organization_field = "software development"
    organization_name = "Roseware Integrations"
    organization_country = "United States"
    organization_state = "Oregon"
    organization_city = "Portland"
    company_details = f"a {organization_field} company, called {organization_name}, from {organization_city} {organization_state}, {organization_country}"
    restrictions_list = [
        "The post should be no more that 500 characters (less is preferred, short and sweet), This is the most important rule",
        "Your response should only have a json object with a 'caption' field, this is the second most important rule.",
        "Do not make up any events, organizations, festivals, people or places that you were not explicitly told about",
        "Do not state that the organization or company will be present at any events unless it is stated in the events",
    ]
    restrictions = f"Make sure to follow these specific rules very carefully for your response: {', '.join(restrictions_list)}"
    intention = "selling website and business integration tools and profssional websites on https://www.rosewareintegrations.com/"
    system_message = restrictions
    platform_names = '& '.join(platform.name for platform in platforms)
    user_message = ' '.join(textwrap.dedent(f"""
        Using the given topic and title, create a social media post for {platform_names} for {company_details} . The topic and title of the post
        are, topic: {daily_content.daily_topic}, title: {daily_content.title}. The date is {datetime.now()}, and the marketing intention is
        {intention}. Keep the tone light and fun, but not too silly. Don't use any big words or complicated sentences.
        Do not make up any events, organizations, festivals, people or places that you were not explicitly told about
    """).split())

    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            max_tokens=token_limit,  # Increase the max_tokens to allow the model to generate a more complete response
            temperature=1,  # Lower temperature makes the output more focused and deterministic
        )
        # Parse the response to get the caption
        response_content = response['choices'][0]['message']['content']
        parsed_content = json.loads(response_content)
        caption = parsed_content["caption"]
        
        # Generate an image for the caption
        image_prompt = f'Create a {platform_names} image, with no words, for the caption "{caption}"'
        response = openai.Image.create(
            prompt=image_prompt,
            n=1,
            size="1024x1024"
        )
        image_url = response['data'][0]['url']
        
        # Create the post
        for platform in platforms:
            new_social_post = SocialPost(
                caption=caption,
                image_url=image_url,
                platform=platform.name
            )
            new_social_post.save()
        return True
    except Exception as error:
        logger.error(error)
        return False
