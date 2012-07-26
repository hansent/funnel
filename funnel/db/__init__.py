import datetime
import sqlalchemy
from sqlalchemy import create_engine, Column
from sqlalchemy.orm import scoped_session, sessionmaker, object_mapper
from sqlalchemy.orm.properties import ColumnProperty, RelationshipProperty
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from funnel.util import cached_property, cached_classproperty


class DataBase(object):
    def __init__(self, uri='sqlite:////tmp/test.db', echo=False):
        self.engine = create_engine(uri, echo=echo, convert_unicode=True)
        self.Model = declarative_base(bind=self.engine, cls=ModelBase)
        self.Model.DB = self

    def get_session(self, **kwargs):
        kwargs.setdefault('autocommit', False)
        kwargs.setdefault('autoflush', False)
        kwargs.setdefault('bind', self.engine)
        session_maker = sessionmaker(**kwargs)
        return scoped_session(session_maker)

    @cached_property
    def session(self, **kwargs):
        return self.get_session()

    def create_all(self):
        self.Model.metadata.create_all()

    def drop_all(self):
        self.Model.metadata.drop_all()

    def many_to_many(self, table_name, table1, table2):
        col1, col2 = "%s_id" % table1, "%s_id" % table2
        key1, key2 = "%s.id" % table1, "%s.id" % table2
        return sqlalchemy.Table(table_name, self.Model.metadata,
            Column(col1, sqlalchemy.Integer, sqlalchemy.ForeignKey(key1)),
            Column(col2, sqlalchemy.Integer, sqlalchemy.ForeignKey(key2))
        )


class ModelBase(object):
    id =  Column(sqlalchemy.Integer, primary_key=True)
    created_at = Column(sqlalchemy.DateTime, default=datetime.datetime.now)

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    @cached_classproperty
    def property_names(cls):
        return [k for k in cls._sa_class_manager]

    @cached_classproperty
    def query(cls):
        return cls.DB.session.query_property()

    @classmethod
    def get(cls, uid):
        return cls.query.get(uid)

    @classmethod
    def get_by_id(cls, uid):
        return cls.query.get(int(uid))

    @classmethod
    def find_one(cls, **kwargs):
        return cls.query.filter_by(**kwargs).first()

    @classmethod
    def find_all(cls, **kwargs):
        return cls.query.filter_by(**kwargs).all()

    def put(self, commit=True, session=None):
        session = session or self.DB.session
        session.add(self)
        if commit:
            self.DB.session.commit()
        return self

    def delete(self, commit=True, session=None):
        session = session or self.DB.session
        session.delete(self)
        if commit:
            self.DB.session.commit()

    def to_dict(self, follow_rel=1, exclude=None):
        result = {}
        exclude = exclude or ()
        mapper = object_mapper(self)
        for prop in mapper.iterate_properties:
            if prop.key in exclude:
                continue
            if isinstance(prop, ColumnProperty):
                result[prop.key] = getattr(self, prop.key)
                continue
            if follow_rel and isinstance(prop, RelationshipProperty):
                rel = result[prop.key] = getattr(self, prop.key)
                if rel == None:
                    continue
                _follow = max(int(follow_rel - 1),0)
                _exclude = (key.name for key in prop.remote_side)
                if isinstance(rel, list):
                    rel_list = [r.to_dict(_follow, _exclude) for r in rel]
                    result[prop.key] = rel_list
                else:
                    result[prop.key] = rel.to_dict(_follow, _exclude)
        return result

    def __jsonic__(self):
        return self.to_dict()

    def __repr__(self):
        return "<%s id=%s>" % (self.__class__.__name__, self.id)





def BooleanColumn(**kwargs):
    return Column(sqlalchemy.Boolean, **kwargs)

def DateColumn(**kwargs):
    return Column(sqlalchemy.Date, **kwargs)

def DateTimeColumn(**kwargs):
    return Column(sqlalchemy.DateTime, **kwargs)

def FloatColumn(**kwargs):
    return Column(sqlalchemy.Float, **kwargs)

def IntegerColumn(**kwargs):
    return Column(sqlalchemy.Integer, **kwargs)

def StringColumn(**kwargs):
    length = kwargs.pop('length', None)
    return Column(StringUTF8(length), **kwargs)

def TextColumn(**kwargs):
    length = kwargs.pop('length', None)
    return Column(TextUTF8(length), **kwargs)

def TimeColumn(**kwargs):
    length = kwargs.pop('length', None)
    return Column(sqlalchemy.String(length), **kwargs)

def ForeignKey(fkey):
    return Column(sqlalchemy.Integer, sqlalchemy.ForeignKey(fkey))

def Relationship(*args, **kwargs):
    return sqlalchemy.orm.relationship(*args, **kwargs)

class StringUTF8(sqlalchemy.TypeDecorator):
    impl = sqlalchemy.Unicode
    def process_bind_param(self, value, dialect):
        if isinstance(value, str):
            value = value.decode('utf-8')
        return value

class TextUTF8(sqlalchemy.TypeDecorator):
    impl = sqlalchemy.UnicodeText
    def process_bind_param(self, value, dialect):
        if isinstance(value, str):
            value = value.decode('utf-8')
        return value

