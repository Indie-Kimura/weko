# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016-2019 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Implementation of various utility functions."""

import mimetypes

import six
import sqlalchemy as sa
from flask import current_app
from invenio_db import db
from invenio_records_files.models import RecordsBuckets
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.utils import import_string

from invenio_files_rest.models import Bucket, FileInstance, Location, \
    ObjectVersion

ENCODING_MIMETYPES = {
    'gzip': 'application/gzip',
    'compress': 'application/gzip',
    'bzip2': 'application/x-bzip2',
    'xz': 'application/x-xz',
}
"""Mapping encoding to MIME types which are not in mimetypes.types_map."""


def obj_or_import_string(value, default=None):
    """Import string or return object.

    :params value: Import path or class object to instantiate.
    :params default: Default object to return if the import fails.
    :returns: The imported object.
    """
    if isinstance(value, six.string_types):
        return import_string(value)
    elif value:
        return value
    return default


def load_or_import_from_config(key, app=None, default=None):
    """Load or import value from config.

    :returns: The loaded value.
    """
    app = app or current_app
    imp = app.config.get(key)
    return obj_or_import_string(imp, default=default)


def guess_mimetype(filename):
    """Map extra mimetype with the encoding provided.

    :returns: The extra mimetype.
    """
    m, encoding = mimetypes.guess_type(filename)
    if encoding:
        m = ENCODING_MIMETYPES.get(encoding, None)
    return m or 'application/octet-stream'


def _location_has_quota(bucket, content_length):
    quota = bucket.location.quota_size
    size = bucket.location.size
    if not quota:
        return True
    if not content_length:
        return True
    return content_length + size + 1 < quota


def delete_file_instance(file_id):
    """Delete file instance."""
    obj_list = ObjectVersion.query.filter_by(
        file_id=file_id).all()
    if len(obj_list) == 0:
        file_instance = FileInstance.get(file_id)
        file_instance.delete()
        file_instance.storage().delete()
        return True
    else:
        return False


def remove_file_cancel_action(bucket_id):
    """Remove file when cancel action.

    Args:
        bucket_id: Bucket ID.
    """
    if bucket_id:
        _bucket = Bucket.get(bucket_id)
        if _bucket.id:
            RecordsBuckets.query.filter_by(bucket_id=_bucket.id).delete()
            object_versions = ObjectVersion.query.filter_by(
                bucket_id=_bucket.id
            ).all()
            _bucket.remove()
            for object_version in object_versions:
                if object_version.file_id:
                    delete_file_instance(object_version.file_id)


def update_location_size():
    """Update location size by total FileInstances size."""
    try:
        find_and_update_location_size()
    except SQLAlchemyError:
        db.session.rollback()
    finally:
        db.session.commit()
        db.session.close()


def find_and_update_location_size():
    """Find and update location size by FileInstances size."""
    ret = db.session.query(
        Location.id,
        sa.func.sum(FileInstance.size),
        Location.size
    ).filter(
        FileInstance.uri.like(sa.func.concat(Location.uri, '%'))
    ).group_by(Location.id)

    for row in ret:
        if row[1] != row[2]:
            with db.session.begin_nested():
                loc = db.session.query(Location).filter(
                    Location.id == row[0]).one()
                loc.size = row[1]
