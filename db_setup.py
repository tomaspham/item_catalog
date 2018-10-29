# Imports
# ===================
from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy import asc
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, Query
from sqlalchemy.orm.exc import NoResultFound

Base = declarative_base()

# DB
# ===================
# Connect to database
engine = create_engine('sqlite:///item_catalog.db')
# Create session
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()


# User setup
class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    email = Column(String(250))
    picture = Column(String)


# User helper functions
def create_user(login_session):
    new_user = User(name=login_session['username'],
                    email=login_session['email'],
                    picture=login_session['picture'])
    session.add(new_user)
    session.commit()
    return new_user.id


def get_user(user_id: int) -> Query:
    user = session.query(User).filter_by(id=user_id).one()
    return user


def get_user_id(email: str) -> int:
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except NoResultFound:
        return None


# Category setup
class Category(Base):
    __tablename__ = 'category'

    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)

    @property
    def serialize(self):
        return {
            'id': self.id,
            'name': self.name
        }


# Category helper functions
def create_category(name: str) -> int:
    new_category = Category(name=name)
    session.add(new_category)
    session.commit()
    return new_category.id


def get_category(category_id: int) -> Category:
    category = session.query(Category).filter_by(id=category_id).one()
    return category


def get_category_id(name: str) -> int:
    category = session.query(Category).filter_by(name=name).one()
    return category.id


def get_items_in_category(category_id: int) -> Query:
    items_list = session.query(Item).join(Item.category).filter_by(
        id=category_id)
    return items_list


def get_all_categories() -> Query:
    categories = session.query(Category).order_by(asc(Category.name))
    return categories


# Item setup
class Item(Base):
    __tablename__ = 'item'

    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    description = Column(Text)
    category_id = Column(Integer, ForeignKey('category.id'))
    category = relationship(Category)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    @property
    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category.name
        }


# Item helper functions
def create_item(name: str, description: str, category_id: int,
                user_id: int) -> Item:
    new_item = Item(name=name, description=description,
                    category_id=category_id, user_id=user_id)
    session.add(new_item)
    session.commit()
    return new_item


def get_item(item_id: int) -> Query:
    item = session.query(Item).filter_by(id=item_id).one()
    return item


def delete_item(item: Query):
    session.delete(item)
    session.commit()


def edit_item(item: Query, name: str, description: str,
              category_id: int) -> Query:
    item.name = name
    item.description = description
    item.category_id = category_id
    session.add(item)
    session.commit()
    return item


if __name__ == '__main__':
    Base.metadata.create_all(engine)
