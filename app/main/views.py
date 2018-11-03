import logging
from sqlalchemy import exc
from flask import Flask, render_template
from . import main


@main.route('/')
def root():
    # For the sake of example, use static information to inflate the template.
    # This will be replaced with real information in later steps.

    return render_template('index.html', times = dummy_times)

