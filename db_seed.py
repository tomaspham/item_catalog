# Imports
# ===================
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound

from db_setup import Base, User, Category, Item, engine

Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()


def create_user(name, email, picture):
    new_user = User(name=name, email=email, picture=picture)
    session.add(new_user)
    session.commit()
    return new_user.id


def get_user(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def get_user_id(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except NoResultFound:
        return None


def create_category(name):
    new_category = Category(name=name)
    session.add(new_category)
    session.commit()
    return new_category.id


def get_category_id(name):
    category = session.query(Category).filter_by(name=name).one()
    return category.id


def get_items_in_category(category_name):
    items_list = session.query(Item).join(Item.category).filter_by(
        name=category_name)
    return items_list


def create_item(name, description, category_id, user_id):
    new_item = Item(name=name, description=description,
                    category_id=category_id, user_id=user_id)
    session.add(new_item)
    session.commit()
    return new_item.id


def add_users():
    user_list = [
        ['admin user', 'admin@localhost.com', 'https://bit.ly/2PooNj6']
    ]

    for user in user_list:
        create_user(user[0], user[1], user[2])


def seed_categories():
    category_list = [
        'Fake',
        'Something',
        'Foo'
    ]

    for category in category_list:
        create_category(category)


def seed_items():
    item_list = [
        (
            'Bar',
            'Common variable name for testing purposes',
            'Foo'
        ),
        (
            'Item',
            'Fake item in our db',
            'Fake'
        ),
        (
            'Record',
            'Fake record in our db',
            'Fake'
        )
    ]

    for item in item_list:
        create_item(item[0], item[1], get_category_id(item[2]), 1)


if __name__ == '__main__':
    add_users()
    seed_categories()
    seed_items()
