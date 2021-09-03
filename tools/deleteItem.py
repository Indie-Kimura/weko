import os
import sys
import traceback

from elasticsearch.exceptions import NotFoundError as NotFoundError_es
from flask import current_app
from invenio_db import db
from invenio_files_rest.models import Bucket, FileInstance, ObjectVersion
from invenio_pidstore.models import PersistentIdentifier
from invenio_records_files.api import FileObject, Record
from invenio_records_files.models import RecordsBuckets
from sqlalchemy.exc import SQLAlchemyError
from weko_deposit.api import WekoRecord
from weko_records.models import ItemMetadata, ItemReference

from elasticsearch import Elasticsearch, helpers


def deleteItem(id):
    object_uuid_list = []
    itemid_list = []
    pid = PersistentIdentifier.get(
        pid_type="parent", pid_value="parent:{0}".format(id))
    current_app.logger.debug(pid)
    object_uuid_list.append(pid.object_uuid)
    itemid_list.append(id)

    ret = PersistentIdentifier.query.filter(
        PersistentIdentifier.pid_value.like("{0}.%".format(id)))

    for i in ret.all():
        object_uuid_list.append(i.object_uuid)
        if i.pid_type == 'recid':
            itemid_list.append(i.pid_value)

    """ remvoe duplicated uuid """
    object_uuid_list = list(set(object_uuid_list))
    itemid_list = list(set(itemid_list))

    current_app.logger.debug(itemid_list)

    es = Elasticsearch(
        "http://"+os.environ.get('INVENIO_ELASTICSEARCH_HOST', 'localhost')+":9200")
    query = '{"query":{"bool":{"should":['
    for i in itemid_list:
        query = query + '{"term":{"pid_value":{"value":"'+str(i)+'"}}},'

    query = query[:len(query)-1]
    query = query + ']}}}'

    current_app.logger.debug('query: {0}'.format(query))

    try:
        result = es.delete_by_query(index=os.environ.get(
            'SEARCH_INDEX_PREFIX', 'tenant1')+"-stats-item-create", body=query, conflicts='proceed')
    except NotFoundError_es:
        current_app.logger.error(traceback.format_exc())

    try:
        result = es.delete_by_query(index=os.environ.get(
            'SEARCH_INDEX_PREFIX', 'tenant1')+"-events-stats-item-create", body=query, conflicts='proceed')
    except NotFoundError_es:
        current_app.logger.error(traceback.format_exc())

    try:
        result = es.delete_by_query(index=os.environ.get(
            'SEARCH_INDEX_PREFIX', 'tenant1')+"-stats-record-view", body=query, conflicts='proceed')
    except NotFoundError_es:
        current_app.logger.error(traceback.format_exc())

    try:
        result = es.delete_by_query(index=os.environ.get(
            'SEARCH_INDEX_PREFIX', 'tenant1')+"-events-stats-record-view", body=query, conflicts='proceed')
    except NotFoundError_es:
        current_app.logger.error(traceback.format_exc())

    query = '{"query":{"bool":{"should":['
    for itemid in itemid_list:
        query = query + \
            '{"term":{"control_number":{"value":"'+str(itemid)+'"}}},'

    query = query[:len(query)-1]
    query = query + ']}}}'

    try:
        result = es.delete_by_query(index=os.environ.get(
            'SEARCH_INDEX_PREFIX', 'tenant1')+"-weko", body=query, conflicts='proceed')
    except NotFoundError_es:
        current_app.logger.error(traceback.format_exc())

    for uid in object_uuid_list:
        try:
            with db.session.no_autoflush:
                record = Record.get_record(uid)
                if record.files:
                    for obj in record.files:
                        f = FileInstance.get(obj.file_id)
                        ObjectVersion.query.filter_by(
                            file_id=obj.file_id).delete()
                        f.delete()
                        f.storage().delete()
                        b = Bucket.get(obj.bucket_id)
                        b.delete(bucket_id=obj.bucket_id)
                        current_app.logger.debug(
                            "version_id {0}".format(obj.version_id))
                        current_app.logger.debug(
                            "bucket_id {0}".format(obj.bucket_id))
                        current_app.logger.debug(
                            "file_id {0}".format(obj.file_id))
                        current_app.logger.debug(
                            "delete {0}".format(f.uri))
                record.delete(force=True)
                db.session.commit()
            current_app.logger.debug("hard delete {0}".format(record.id))
        except SQLAlchemyError:
            current_app.logger.error(traceback.format_exc())
            db.session.rollback()

        try:
            with db.session.no_autoflush:
                ItemMetadata.query.filter_by(id=uid).delete()
                db.session.commit()
            current_app.logger.debug(
                "delete ItemMetadata {0}".format(uid))
        except SQLAlchemyError:
            current_app.logger.error(traceback.format_exc())
            db.session.rollback()

    for uid in object_uuid_list:
        try:
            with db.session.no_autoflush:
                PersistentIdentifier.query.filter_by(object_uuid=uid).delete()
                db.session.commit()
                current_app.logger.debug(
                    "delete PersistentIdentifier {0}".format(uid))
        except SQLAlchemyError:
            current_app.logger.error(traceback.format_exc())
            db.session.rollback()


if __name__ == '__main__':
    args = sys.argv
    deleteItem(args[1])
