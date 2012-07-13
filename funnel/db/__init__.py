import sqlalchemy
from sqlalchemy import create_engine, Column
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import scoped_session, sessionmaker


class cached_property(object):
    def __init__(self, fget, doc=None):
        self.fget = fget
        self.__doc__ = doc or fget.__doc__
        self.__name__ = fget.__name__
        self.__module__ = fget.__module__

    def __get__(self, obj, cls):
        if obj is None:
            return self
        setattr(obj, self.__name__, self.fget(obj))
        return getattr(obj, self.__name__)


class cached_classproperty(cached_property):
    def __get__(self, obj, cls):
        setattr(cls, self.__name__, self.fget(cls))
        return getattr(cls, self.__name__)


class DataBase(object):
    def __init__(self, uri='sqlite:////tmp/test.db', echo=True):
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


class ModelBase(object):
    id =  Column(sqlalchemy.Integer, primary_key=True)

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    @cached_classproperty
    def query(cls):
        return cls.DB.session.query_property()

    def __repr__(self):
        return "<%s id=%s>" % (self.__class__.__name__, self.id)

    def delete(self, commit=False, session=None):
        session = session or self.DB.session
        session.delete(self)
        if commit:
            self.DB.session.commit()

    def put(self, commit=False, session=None):
        session = session or self.DB.session
        session.add(self)
        if commit:
            self.DB.session.commit()
        return self


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

