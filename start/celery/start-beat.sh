#!/bin/bash
celery -A roseware worker -B -l ERROR

