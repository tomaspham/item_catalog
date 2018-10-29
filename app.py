# Imports
# ===================
import json
import random
import string
import time
from functools import wraps

import httplib2
import requests
from flask import (Flask, render_template, request, redirect,
                   jsonify, url_for, flash, make_response,
                   session as login_session)
from oauth2client.client import FlowExchangeError
from oauth2client.client import flow_from_clientsecrets
from sqlalchemy import asc, desc
from sqlalchemy.orm import sessionmaker

import db_setup as db
from db_setup import Base, Category, Item, engine

# Flask instance
# ===================
app = Flask(__name__)

# DB
# ===================
# Connect to database
Base.metadata.bind = engine
# Create session
DBSession = sessionmaker(bind=engine)
session = DBSession()

CLIENT_ID = json.loads(open('client_secrets.json', 'r').read())['web'][
    'client_id']
APPLICATION_NAME = 'Item Catalog'


# Login decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in login_session:
            return redirect(url_for('show_login'))
        return f(*args, **kwargs)

    return decorated_function


# Login Routing
# ===================
# Login - Create anti-forgery state token
@app.route('/login')
def show_login():
    """login page"""
    state = ''.join(
        random.choice(string.ascii_uppercase + string.digits) for x in
        range(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


# Google login
@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data
    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Check that the access token is valid.
    access_token = credentials.access_token
    url = f'https://www.googleapis.com/oauth2/v1/' \
          f'tokeninfo?access_token={access_token}'
    # Submit request, parse response
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps('Token\'s user ID doesn\'t match given user ID.'), 401)
        response.heads['Content-Type'] = 'application/json'
        return response
    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps('Token\'s client ID does not match app\'s.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(
            json.dumps('Current user is already connected'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Store the access token in the session for later use.
    login_session['access_token'] = access_token
    login_session['gplus_id'] = gplus_id
    # Get user info
    userinfo_url = 'https://www.googleapis.com/oauth2/v1/userinfo'
    params = {
        'access_token': credentials.access_token,
        'alt': 'json'
    }
    answer = requests.get(userinfo_url, params=params)
    data = answer.json()
    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    login_session['provider'] = 'google'
    # see if user exists, if it doesn't make a new one
    user_id = db.get_user_id(login_session['email'])
    if user_id is None:
        user_id = db.create_user(login_session)
    login_session['user_id'] = user_id
    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += '" style = "width: 300px; height: 300px;' \
              'border-radius: 150px;-webkit-border-radius: ' \
              '150px;-moz-border-radius: 150px;"> '
    flash('You are now logged in as {name}'.format(
        name=login_session['username']))
    return output


# Google logout
@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(json.dumps('Current user not connected'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token={token}'.format(
        token=access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    if result['status'] != '200':
        response = make_response(
            json.dumps('Failed to revoke token for given user.'), 400)
        response.headers['Content-Type'] = 'application/json'
        return response


# logout + redirect
@app.route('/disconnect')
def disconnect():
    if 'provider' in login_session:
        gdisconnect()
        # Reset the user's sesson.
        del login_session['gplus_id']
        del login_session['user_id']
        del login_session['access_token']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['provider']

        flash('You have been successfully logged out.')
    else:
        flash('You were not logged in.')

    return redirect(url_for('item_catalog'))


# Flask Routing
# ===================
@app.route('/')
@app.route('/category')
def item_catalog():
    """front page with recent added items"""
    categories = db.get_all_categories()
    items = session.query(Item).order_by(desc(Item.id)).limit(10)
    return render_template('latest_items.html', categories=categories,
                           items=items)

@app.route('/category/<int:category_id>/')
def show_category(category_id):
    """category page"""
    categories = db.get_all_categories()
    cat = db.get_category(category_id)
    items = session.query(Item).filter_by(category_id=cat.id).order_by(
        asc(Item.name))
    return render_template('category.html', categories=categories,
                           category=cat, items=items)


@app.route('/category/<int:category_id>/<int:item_id>/')
def show_item(category_id, item_id):
    """item page"""
    categories = db.get_all_categories()
    category = db.get_category(category_id)
    item = db.get_item(item_id)
    return render_template('item.html', categories=categories,
                           category=category, item=item)


@app.route('/category/new/', defaults={'category_id': None},
           methods=['GET', 'POST'])
@app.route('/category/new/<int:category_id>/', methods=['GET', 'POST'])
@login_required
def add_item(category_id):
    """add item page"""
    categories = db.get_all_categories()
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        category = request.form['category']
        values = {}
        user_id = login_session['user_id']
        if name and description and category != "None":
            flash('Added')
            cat_id = db.get_category_id(category)
            new_item = db.create_item(name, description, cat_id, user_id)
            return redirect(
                url_for('show_item', category_id=cat_id, item_id=new_item.id))
        elif category == "None":
            flash('Please select a category')
        else:
            values['empty'] = category
            flash('Invalid values')
        values['input_name'] = name
        values['input_description'] = description
        return render_template('add_item.html', categories=categories,
                               **values)
    else:
        if category_id:
            category_name = db.get_category(category_id).name
            return render_template('add_item.html', categories=categories,
                                   empty=category_name)
        else:
            return render_template('add_item.html', categories=categories)


@app.route('/category/<int:category_id>/<int:item_id>/edit/',
           methods=['GET', 'POST'])
@login_required
def edit_item(category_id, item_id):
    """edit item page"""
    categories = db.get_all_categories()
    category = db.get_category(category_id)
    item = db.get_item(item_id)
    user_id = login_session['user_id']
    if item.user_id != user_id:
        return redirect(url_for('item_catalog'))
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        category = request.form['category']
        values = {}
        if name and description:
            flash('Edit successful')
            db.edit_item(item, name, description, db.get_category_id(category))
            time.sleep(1)
            return redirect(
                url_for('show_item', category_id=category_id, item_id=item_id))
        else:
            values['empty'] = category
            flash('Invalid values')
        values['input_name'] = name
        values['input_description'] = description
        return render_template('add_item.html', categories=categories,
                               **values)
    else:
        return render_template('edit_item.html', category_id=category_id,
                               item_id=item_id, categories=categories,
                               input_name=item.name,
                               input_description=item.description,
                               empty=category.name)


@app.route('/category/<int:category_id>/<int:item_id>/delete/',
           methods=['GET', 'POST'])
@login_required
def delete_item(category_id, item_id):
    """delete item page"""
    cat = db.get_category(category_id)
    item = db.get_item(item_id)
    user_id = login_session['user_id']
    if item.user_id != user_id:
        return redirect(url_for('item_catalog'))
    if request.method == 'POST':
        delete_confirmation = request.form['delete']
        if delete_confirmation == 'yes':
            db.delete_item(item)
            flash('Item deleted')
        return redirect(url_for('show_category', category_id=cat.id))
    else:
        return render_template('delete_item.html', category=cat, item=item)


# JSONs
@app.route('/category/json')
def categories_json():
    categories = session.query(Category).all()
    return jsonify(Categories=[cat.serialize for cat in categories])


@app.route('/category/<int:category_id>/json')
def category_items_json(category_id):
    item_list = db.get_items_in_category(category_id)
    category = db.get_category(category_id)
    return jsonify(Category=category.name,
                   Items=[item.serialize for item in item_list])


@app.route('/category/<int:category_id>/<int:item_id>/json')
def item_json(category_id, item_id):
    item = db.get_item(item_id)
    return jsonify(Item=item.serialize)


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
