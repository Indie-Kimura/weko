# -*- coding: utf-8 -*-
#
# Copyright (C) 2019 National Institute of Informatics.
#
# WEKO-Items-Autofill is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Pytest configuration.

See https://pytest-invenio.readthedocs.io/ for documentation on which test
fixtures are available.
"""

from __future__ import absolute_import, print_function

import pytest
from flask import Flask
from flask_babelex import Babel


@pytest.fixture(scope='module')
def celery_config():
    """Override pytest-invenio fixture.

    TODO: Remove this fixture if you add Celery support.
    """
    return {}


@pytest.fixture(scope='module')
def create_app(instance_path):
    """Application factory fixture."""
    def factory(**config):
        from weko_items_autofill import WekoItemsAutofill
        from weko_items_autofill.views import blueprint
        app = Flask('testapp', instance_path=instance_path)
        app.config.update(**config)
        Babel(app)
        WekoItemsAutofill(app)
        app.register_blueprint(blueprint)
        return app
    return factory
