# -*- coding: utf-8 -*-
#
# Copyright (C) 2019 National Institute of Informatics.
#
# weko-gridlayout is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Pytest configuration.

See https://pytest-invenio.readthedocs.io/ for documentation on which test
fixtures are available.
"""

from __future__ import absolute_import, print_function

import os
import shutil
import tempfile

import pytest
from mock import patch
from flask import Flask
from flask_admin import Admin
from flask_babelex import Babel
from sqlalchemy_utils.functions import create_database, database_exists

from invenio_accounts import InvenioAccounts
from invenio_accounts.testutils import create_test_user, login_user_via_session
from invenio_access.models import ActionUsers
from invenio_access import InvenioAccess
from invenio_db import InvenioDB, db as db_

from invenio_accounts.models import User, Role
from weko_gridlayout import WekoGridLayout
#from weko_admin import WekoAdmin
from weko_gridlayout.views import blueprint, blueprint_api
from weko_gridlayout.services import WidgetItemServices
from weko_gridlayout.admin import widget_adminview, WidgetSettingView
from weko_gridlayout.models import WidgetType, WidgetItem,WidgetMultiLangData,WidgetDesignSetting,WidgetDesignPage
from weko_admin.models import AdminLangSettings

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
        app = Flask('testapp', instance_path=instance_path)
        app.config.update(**config)
        Babel(app)
        InvenioAccounts(app)
        WekoGridLayout(app)

        return app
    return factory

@pytest.yield_fixture()
def instance_path():
    path = tempfile.mkdtemp()
    yield path
    shutil.rmtree(path)


@pytest.fixture()
def base_app(instance_path):
    app_ = Flask("testapp", instance_path=instance_path)
    app_.config.update(
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            'SQLALCHEMY_DATABASE_URI', 'sqlite:///test.db'),
        TESTING=True,
        SECRET_KEY='SECRET_KEY',
    )
    Babel(app_)
    InvenioDB(app_)
    InvenioAccounts(app_)
    InvenioAccess(app_)
    #WekoAdmin(app_)
    app_.register_blueprint(blueprint)
    app_.register_blueprint(blueprint_api)

    return app_


@pytest.yield_fixture()
def app(base_app):
    with base_app.app_context():
        yield base_app

@pytest.yield_fixture()
def client(app):
    with app.test_client() as client:
        yield client


@pytest.fixture()
def db(app):
    """Database fixture."""
    if not database_exists(str(db_.engine.url)):
        create_database(str(db_.engine.url))
    db_.create_all()
    yield db_
    db_.session.remove()
    db_.drop_all()


@pytest.fixture()
def users(app, db):
    """Create users."""
    ds = app.extensions['invenio-accounts'].datastore
    user_count = User.query.filter_by(email='user@test.org').count()
    if user_count != 1:
        user = create_test_user(email='user@test.org')
        contributor = create_test_user(email='contributor@test.org')
        comadmin = create_test_user(email='comadmin@test.org')
        repoadmin = create_test_user(email='repoadmin@test.org')
        sysadmin = create_test_user(email='sysadmin@test.org')
        generaluser = create_test_user(email='generaluser@test.org')
        originalroleuser = create_test_user(email='originalroleuser@test.org')
        originalroleuser2 = create_test_user(email='originalroleuser2@test.org')
    else:
        user = User.query.filter_by(email='user@test.org').first()
        contributor = User.query.filter_by(email='contributor@test.org').first()
        comadmin = User.query.filter_by(email='comadmin@test.org').first()
        repoadmin = User.query.filter_by(email='repoadmin@test.org').first()
        sysadmin = User.query.filter_by(email='sysadmin@test.org').first()
        generaluser = User.query.filter_by(email='generaluser@test.org')
        originalroleuser = create_test_user(email='originalroleuser@test.org')
        originalroleuser2 = create_test_user(email='originalroleuser2@test.org')

    role_count = Role.query.filter_by(name='System Administrator').count()
    if role_count != 1:
        sysadmin_role = ds.create_role(name='System Administrator')
        repoadmin_role = ds.create_role(name='Repository Administrator')
        contributor_role = ds.create_role(name='Contributor')
        comadmin_role = ds.create_role(name='Community Administrator')
        general_role = ds.create_role(name='General')
        originalrole = ds.create_role(name='Original Role')
    else:
        sysadmin_role = Role.query.filter_by(name='System Administrator').first()
        repoadmin_role = Role.query.filter_by(name='Repository Administrator').first()
        contributor_role = Role.query.filter_by(name='Contributor').first()
        comadmin_role = Role.query.filter_by(name='Community Administrator').first()
        general_role = Role.query.filter_by(name='General').first()
        originalrole = Role.query.filter_by(name='Original Role').first()

    ds.add_role_to_user(sysadmin, sysadmin_role)
    ds.add_role_to_user(repoadmin, repoadmin_role)
    ds.add_role_to_user(contributor, contributor_role)
    ds.add_role_to_user(comadmin, comadmin_role)
    ds.add_role_to_user(generaluser, general_role)
    ds.add_role_to_user(originalroleuser, originalrole)
    ds.add_role_to_user(originalroleuser2, originalrole)
    ds.add_role_to_user(originalroleuser2, repoadmin_role)

    # Assign access authorization
    with db.session.begin_nested():
        action_users = [
            ActionUsers(action='superuser-access', user=sysadmin)
        ]
        db.session.add_all(action_users)

    return [
        {'email': contributor.email, 'id': contributor.id, 'obj': contributor},
        {'email': repoadmin.email, 'id': repoadmin.id, 'obj': repoadmin},
        {'email': sysadmin.email, 'id': sysadmin.id, 'obj': sysadmin},
        {'email': comadmin.email, 'id': comadmin.id, 'obj': comadmin},
        {'email': generaluser.email, 'id': generaluser.id, 'obj': sysadmin},
        {'email': originalroleuser.email, 'id': originalroleuser.id, 'obj': originalroleuser},
        {'email': originalroleuser2.email, 'id': originalroleuser2.id, 'obj': originalroleuser2},
        {'email': user.email, 'id': user.id, 'obj': user},
    ]


@pytest.fixture()
def widget_item(db):
    insert_obj = \
        {"1": {
            "repository_id": "Root Index",
            "widget_type": "Free description",
            "is_enabled": True,
            "is_deleted": False,
            "locked": False,
            "locked_by_user": None,
            "multiLangSetting": {
                "en": {
                    "label": "for test"
                }
            }
        }}
    for i in insert_obj:
        with patch("weko_gridlayout.models.WidgetItem.get_sequence", return_value=i):
            WidgetItemServices.create(insert_obj[str(i)])
    widget_data = WidgetItem.query.all()
    return widget_data


@pytest.fixture()
def widget_items(db):
    insert_obj = \
        {"1": {
            "repository_id": "Root Index",
            "widget_type": "Free description",
            "is_enabled": True,
            "is_deleted": False,
            "locked": False,
            "locked_by_user": None,
            "multiLangSetting": {
                "en": {
                    "label": "for test"
                }
            }
        },
        "2": {
            "repository_id": "Root Index",
            "widget_type": "Free description",
            "is_enabled": True,
            "is_deleted": False,
            "locked": False,
            "locked_by_user": None,
            "multiLangSetting": {
                "fil": {
                    "label": "for test2"
                }
            }
        },
        "3": {
            "repository_id": "Root Index",
            "widget_type": "Free description",
            "is_enabled": True,
            "is_deleted": False,
            "locked": False,
            "locked_by_user": None,
            "multiLangSetting": {
                "hi": {
                    "label": "for test3"
                }
            }
        }}
    for i in insert_obj:
        with patch("weko_gridlayout.models.WidgetItem.get_sequence", return_value=i):
            WidgetItemServices.create(insert_obj[str(i)])
    widget_data = WidgetItem.query.all()
    return widget_data


@pytest.fixture()
def admin_view(app, db, view_instance):
    """Admin view fixture"""
    assert isinstance(widget_adminview, dict)

    assert 'model' in widget_adminview
    assert 'modelview' in widget_adminview
    admin = Admin(app, name="Test")

    widget_adminview_copy = dict(widget_adminview)
    widget_model = widget_adminview_copy.pop('model')
    widget_view = widget_adminview_copy.pop('modelview')
    #admin.add_view(widget_view(widget_model, db.session, **widget_adminview_copy))

    #admin.add_view(widget_adminview['modelview'](
    #    widget_adminview['model'], db.session,
    #    category=widget_adminview['category']))
    admin.add_view(view_instance)


@pytest.fixture()
def view_instance(app, db):
    view = WidgetSettingView(WidgetItem, db.session)
    return view


@pytest.fixture()
def admin_lang_settings(db):
    AdminLangSettings.create(lang_code="en", lang_name="English",
                             is_registered=True, sequence=1, is_active=True)
    AdminLangSettings.create(lang_code="fil", lang_name="Filipino (Pilipinas)",
                             is_registered=False, sequence=0, is_active=True)

def db_register(users,db):
    widgettype_0 = WidgetType(type_id='Free description',type_name='Free description')
    widgettype_1 = WidgetType(type_id='Access counter',type_name='Access counter')
    widgettype_2 = WidgetType(type_id='Notice',type_name='Notice')
    widgettype_3 = WidgetType(type_id='New arrivals',type_name='New arrivals')
    widgettype_4 = WidgetType(type_id='Main contents',type_name='Main contents')
    widgettype_5 = WidgetType(type_id='Menu',type_name='Menu')
    widgettype_6 = WidgetType(type_id='Header',type_name='Header')
    widgettype_7 = WidgetType(type_id='Footer',type_name='Footer')

    widgetitem_1 = WidgetItem(widget_id=1,repository_id='Root Index',widget_type='Main contents',settings={"background_color": "#FFFFFF", "label_enable": True, "theme": "default", "frame_border_color": "#DDDDDD", "border_style": "solid", "label_text_color": "#333333", "label_color": "#F5F5F5"},is_enabled=True,is_deleted=False,locked=True,locked_by_user=1)
    widgetitem_2 = WidgetItem(widget_id=2,repository_id='Root Index',widget_type='Free description',settings={"background_color": "#FFFFFF", "label_enable": True, "theme": "default", "frame_border_color": "#DDDDDD", "border_style": "solid", "label_text_color": "#333333", "label_color": "#F5F5F5"},is_enabled=True,is_deleted=False,locked=True,locked_by_user=1)
    widgetitem_3 = WidgetItem(widget_id=3,repository_id='Root Index',widget_type='Access counter',settings={"background_color":"#FFFFFF", "label_enable": True, "theme": "default", "frame_border_color": "#DDDDDD", "border_style": "solid", "label_text_color": "#333333", "label_color": "#F5F5F5", "access_counter": "0", "following_message": "None", "other_message": "None", "preceding_message": "None"},is_enabled=True,is_deleted=False,locked=True,locked_by_user=1)
    widgetitem_4 = WidgetItem(widget_id=4,repository_id='Root Index',widget_type='Notice',settings={"background_color": "#FFFFFF", "label_enable": True, "theme": "default", "frame_border_color": "#DDDDDD", "border_style": "solid", "label_text_color": "#333333", "label_color": "#F5F5F5", "hide_the_rest": "None", "read_more": "None"},is_enabled=True,is_deleted=False,locked=True,locked_by_user=1)
    widgetitem_5 = WidgetItem(widget_id=5,repository_id='Root Index',widget_type='New arrivals',settings={"background_color": "#FFFFFF", "label_enable": True, "theme": "default", "frame_border_color": "#DDDDDD", "border_style": "solid", "label_text_color": "#333333", "label_color": "#F5F5F5", "new_dates": "5", "display_result": "5", "rss_feed": True},is_enabled=True,is_deleted=False,locked=True,locked_by_user=1)
    widgetitem_6 = WidgetItem(widget_id=6,repository_id='Root Index',widget_type='Menu',settings={"background_color": "#FFFFFF", "label_enable": True, "theme": "default", "frame_border_color": "#DDDDDD", "border_style": "solid", "label_text_color": "#333333", "label_color": "#F5F5F5", "menu_orientation": "horizontal", "menu_bg_color": "#ffffff", "menu_active_bg_color": "#ffffff", "menu_default_color": "#000000", "menu_active_color": "#000000", "menu_show_pages": [2]},is_enabled=True,is_deleted=False,locked=True,locked_by_user=1)
    widgetitem_7 = WidgetItem(widget_id=7,repository_id='Root Index',widget_type='Header',settings={"background_color": "#3D7FA1", "label_enable": False, "theme": "simple", "fixedHeaderBackgroundColor": "#FFFFFF", "fixedHeaderTextColor": "#808080"},is_enabled=True,is_deleted=False,locked=True,locked_by_user=1)
    widgetitem_8 = WidgetItem(widget_id=8,repository_id='Root Index',widget_type='Footer',settings={"background_color": "#3D7FA1", "label_enable": False, "theme": "simple"},is_enabled=True,is_deleted=False,locked=True,locked_by_user=1)


    widgetmultilangdata_1=WidgetMultiLangData(widget_id=1,lang_code='en',label='',description_data='null',is_deleted=False)
    widgetmultilangdata_2=WidgetMultiLangData(widget_id=2,lang_code='en',label='',description_data='{"description": "<p>free description</p>"}',is_deleted=False)
    widgetmultilangdata_3=WidgetMultiLangData(widget_id=3,lang_code='en',label='',description_data='"{"access_counter": "0"}',is_deleted=False)
    widgetmultilangdata_4=WidgetMultiLangData(widget_id=4,lang_code='en',label='',description_data='{"description": "<p>notice</p>"}',is_deleted=False)
    widgetmultilangdata_5=WidgetMultiLangData(widget_id=5,lang_code='en',label='',description_data='null',is_deleted=False)
    widgetmultilangdata_6=WidgetMultiLangData(widget_id=5,lang_code='en',label='',description_data='null',is_deleted=False)
    widgetmultilangdata_7=WidgetMultiLangData(widget_id=6,lang_code='en',label='',description_data='null',is_deleted=False)
    widgetmultilangdata_8=WidgetMultiLangData(widget_id=7,lang_code='en',label='',description_data='{"description": "<p>header</p>"}',is_deleted=False)
    widgetmultilangdata_9=WidgetMultiLangData(widget_id=8,lang_code='en',label='',description_data='{"description": "<p>footer</p>"}',is_deleted=False)

    widget_design_setting_1 = WidgetDesignSetting(repository_id='Root Index',settings=[{"x": 0, "y": 0, "width": 12, "height": 4, "name": "header", "id": "Root Index", "type": "Header", "widget_id": 7, "background_color": "#3D7FA1", "label_enable": False, "theme": "simple", "fixedHeaderBackgroundColor": "#FFFFFF", "fixedHeaderTextColor": "#808080", "multiLangSetting": {"en": {"label": "header", "description": {"description": "<p>header</p>"}}}}, {"x": 0, "y": 4, "width": 12, "height": 4, "name": "menu", "id": "Root Index", "type": "Menu", "widget_id": 6, "background_color": "#FFFFFF", "label_enable": True, "theme": "default", "frame_border_color": "#DDDDDD", "border_style": "solid", "label_text_color": "#333333", "label_color": "#F5F5F5", "menu_orientation": "horizontal", "menu_bg_color": "#ffffff", "menu_active_bg_color": "#ffffff", "menu_default_color": "#000000", "menu_active_color": "#000000", "menu_show_pages": [2], "multiLangSetting": {"en": {"label": "menu", "description": None }}}, {"x": 0, "y": 8, "width": 12, "height": 21, "name": "main contents", "id": "Root Index", "type": "Main contents", "widget_id": 1, "background_color": "#FFFFFF", "label_enable": True, "theme": "default", "frame_border_color": "#DDDDDD", "border_style": "solid", "label_text_color": "#333333", "label_color": "#F5F5F5", "multiLangSetting": {"en": {"label": "main contents", "description": None}}}, {"x": 0, "y": 29, "width": 2, "height": 6, "name": "new arrivals", "id": "Root Index", "type": "New arrivals", "widget_id": 5, "background_color": "#FFFFFF", "label_enable": True, "theme": "default", "frame_border_color": "#DDDDDD", "border_style": "solid", "label_text_color": "#333333", "label_color": "#F5F5F5", "new_dates": "5", "display_result": "5", "rss_feed": True, "multiLangSetting": {"en": {"label": "new arrivals", "description": None}}}, {"x": 2, "y": 29, "width": 2, "height": 6, "name": "Free description", "id": "Root Index", "type": "Free description", "widget_id": 2, "background_color": "#FFFFFF", "label_enable": True, "theme": "default", "frame_border_color": "#DDDDDD", "border_style": "solid", "label_text_color": "#333333", "label_color": "#F5F5F5", "multiLangSetting": {"en": {"label": "Free description", "description": {"description": "<p>free description</p>"}}}}, {"x": 4, "y": 29, "width": 2, "height": 6, "name": "access counter", "id": "Root Index", "type": "Access counter", "widget_id": 3, "created_date": "2022-07-19", "background_color": "#FFFFFF", "label_enable": True, "theme": "default", "frame_border_color": "#DDDDDD", "border_style": "solid", "label_text_color": "#333333", "label_color": "#F5F5F5", "access_counter": "0", "following_message": "None", "other_message": "None", "preceding_message": "None", "multiLangSetting": {"en": {"label": "access counter", "description": {"access_counter": "0"}}}}, {"x": 6, "y": 29, "width": 2, "height": 6, "name": "notice", "id": "Root Index", "type": "Notice", "widget_id": 4, "background_color": "#FFFFFF", "label_enable": True, "theme": "default", "frame_border_color": "#DDDDDD", "border_style": "solid", "label_text_color": "#333333", "label_color": "#F5F5F5", "hide_the_rest": "None", "read_more": "None", "multiLangSetting": {"en": {"label": "notice", "description": {"description": "<p>notice</p>"}}}}, {"x": 0, "y": 35, "width": 12, "height": 5, "name": "footer", "id": "Root Index", "type": "Footer", "widget_id": 8, "background_color": "#3D7FA1", "label_enable": False, "theme": "simple", "multiLangSetting": {"en": {"label": "footer", "description": {"description": "<p>footer</p>"}}}}])
    widget_design_setting_2 = WidgetDesignSetting(repository_id='test',settings={})

    widget_design_page_1=WidgetDesignPage(id=1,title='Main Layout',repository_id='Root Index',url='/',template_name='',settings=(),is_main_layout=True)
    widget_design_page_2=WidgetDesignPage(id=2,title='about',repository_id='Root Index',url='/about',template_name='',settings=[{"x": 0, "y": 0, "width": 2, "height": 6, "name": "access counter", "id": "Root Index", "type": "Access counter", "widget_id": 3, "background_color": "#FFFFFF", "label_enable": True, "theme": "default", "frame_border_color": "#DDDDDD", "border_style": "solid", "label_text_color": "#333333", "label_color": "#F5F5F5", "access_counter": "0", "following_message": "None", "other_message": "None", "preceding_message": "None", "multiLangSetting": {"en": {"label": "access counter", "description": {"access_counter": "0"}}}, "created_date": "2022-07-30"}],is_main_layout=False)

    with db.session.begin_nested():
        db.session.add(widgettype_0)
        db.session.add(widgettype_1)
        db.session.add(widgettype_2)
        db.session.add(widgettype_3)
        db.session.add(widgettype_4)
        db.session.add(widgettype_5)
        db.session.add(widgettype_6)
        db.session.add(widgettype_7)
        db.session.add(widgetitem_1)
        db.session.add(widgetitem_2)
        db.session.add(widgetitem_3)
        db.session.add(widgetitem_4)
        db.session.add(widgetitem_5)
        db.session.add(widgetitem_6)
        db.session.add(widgetitem_7)
        db.session.add(widgetitem_8)
        db.session.add(widgetmultilangdata_1)
        db.session.add(widgetmultilangdata_2)
        db.session.add(widgetmultilangdata_3)
        db.session.add(widgetmultilangdata_4)
        db.session.add(widgetmultilangdata_5)
        db.session.add(widgetmultilangdata_6)
        db.session.add(widgetmultilangdata_7)
        db.session.add(widgetmultilangdata_8)
        db.session.add(widgetmultilangdata_9)
        db.session.add(widget_design_setting_1)
        db.session.add(widget_design_setting_2)
        db.session.add(widget_design_page_1)
        db.session.add(widget_design_page_2)
